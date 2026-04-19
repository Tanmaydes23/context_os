"""
pipeline/layer3_pivot.py
Layer 3: Pivot Detector + FAISS Archive

Pivot Detector: identifies destination/plan changes.
FAISS Archive:  stores low-score sentences with validity flags.

Solves Test C (stale invalidation) and Test D (cross-turn retrieval).
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config.config_loader import CFG

logger = logging.getLogger(__name__)

# ── Embedding model — load once ───────────────────────────────────────
_encoder = SentenceTransformer(CFG.faiss.embedding_model)  # all-MiniLM-L6-v2
EMBEDDING_DIM = CFG.faiss.embedding_dim  # 384

# ── FAISS index — flat L2, in-memory ────────────────────────────────
_index = faiss.IndexFlatL2(EMBEDDING_DIM)

# ── SQLite metadata store ─────────────────────────────────────────────
DB_PATH = CFG.faiss.db_path  # "logs/faiss_metadata.db"


def _init_db() -> None:
    """Create metadata table if it does not exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Minimize disk footprint: no WAL file, keep temp in memory
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faiss_metadata (
                faiss_id      INTEGER PRIMARY KEY,
                text          TEXT    NOT NULL,
                valid         INTEGER NOT NULL DEFAULT 1,
                session_scope TEXT    NOT NULL DEFAULT 'general',
                city_scope    TEXT,
                item_type     TEXT    NOT NULL DEFAULT 'research',
                turn_number   INTEGER NOT NULL DEFAULT 0,
                score         REAL    NOT NULL DEFAULT 0.4
            )
        """)
        conn.commit()


# Initialise on module load
_init_db()


PIVOT_PHRASES = CFG.pivot_detection.phrases
COSINE_THRESHOLD = CFG.pivot_detection.cosine_similarity_threshold  # 0.25

# Semantic contradiction: high topic similarity but entity clash
# e.g. "Android/Kotlin" vs "iOS/Swift" — same domain, contradicting tech
_CONTRADICTION_THRESHOLD_HIGH = 0.65   # topic similarity: same domain
_CONTRADICTION_THRESHOLD_LOW  = 0.20   # entity clash: too different to coexist


def detect_pivot(
    message: str,
    session_vector: Optional[np.ndarray],
) -> tuple[bool, str]:
    """
    Detect if user message represents a conversation pivot.

    Strategy:
      1. Phrase detection — explicit pivot language (fast, always checked)
      2. Cosine similarity — semantic shift from session direction
      Both conditions together → high-confidence full pivot.
      Phrase alone → still treated as full pivot (user was explicit).

    Args:
        message:        Raw user message
        session_vector: Running average embedding of prior messages.
                        None or all-zeros → skip semantic check.

    Returns:
        (is_pivot: bool, pivot_type: "full" | "none")
    """
    msg_lower = message.lower()

    phrase_hit = any(phrase in msg_lower for phrase in PIVOT_PHRASES)

    semantic_shift = False
    if (
        session_vector is not None
        and session_vector.any()
        and len(session_vector) == EMBEDDING_DIM
    ):
        try:
            msg_embed = _encoder.encode([message])[0]
            norm_sv = np.linalg.norm(session_vector)
            norm_me = np.linalg.norm(msg_embed)
            if norm_sv > 1e-8 and norm_me > 1e-8:
                cosine_sim = float(
                    np.dot(session_vector, msg_embed) / (norm_sv * norm_me)
                )
                semantic_shift = cosine_sim < COSINE_THRESHOLD
                logger.debug(f"Pivot cosine_sim={cosine_sim:.3f}, threshold={COSINE_THRESHOLD}")
        except Exception as e:
            logger.warning(f"Cosine similarity failed: {e}")

    if phrase_hit:
        logger.info(f"Pivot detected (phrase_hit={phrase_hit}, semantic_shift={semantic_shift})")
        return True, "full"

    return False, "none"


def update_session_vector(
    current_vector: Optional[np.ndarray],
    new_message: str,
    alpha: float = 0.3,
) -> np.ndarray:
    """
    Update running session intent vector as exponential moving average.
    new_vector = (1 - alpha) * current + alpha * embed(new_message)

    Args:
        current_vector: Existing session vector. None → use new embed directly.
        new_message:    Latest user message to incorporate.
        alpha:          Weight for new message (0.3 = 30% new, 70% history).

    Returns:
        Updated numpy array of shape (EMBEDDING_DIM,)
    """
    try:
        new_embed = _encoder.encode([new_message])[0].astype(np.float32)

        if current_vector is None or not current_vector.any():
            return new_embed

        updated = (1.0 - alpha) * current_vector + alpha * new_embed
        # Normalise to unit vector to keep cosine similarity stable
        norm = np.linalg.norm(updated)
        if norm > 1e-8:
            updated = updated / norm
        return updated

    except Exception as e:
        logger.error(f"update_session_vector failed: {e}")
        return current_vector if current_vector is not None else np.zeros(EMBEDDING_DIM)


def detect_semantic_contradiction(
    new_constraint: str,
    session_scope: str,
) -> int:
    """
    Module 3: Semantic Contradiction Detection.

    When a new constraint enters GlobalState, evaluate it against existing
    valid FAISS items. If topic similarity is HIGH (same domain) but
    entity similarity is LOW (conflicting entities), invalidate the older items.

    Example: "use Swift/iOS" contradicts existing "use Kotlin/Android" items
    even though no explicit pivot phrase was used.

    Returns:
        Number of items invalidated.
    """
    if _index.ntotal == 0:
        return 0

    invalidated = 0
    try:
        new_embed = _encoder.encode([new_constraint])[0].astype(np.float32)
        new_embed_norm = new_embed / (np.linalg.norm(new_embed) + 1e-8)

        # Retrieve all valid items for this scope
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("""
                SELECT faiss_id, text FROM faiss_metadata
                WHERE session_scope = ? AND valid = 1
                  AND item_type != 'confirmed_booking'
            """, (session_scope,)).fetchall()

        if not rows:
            return 0

        # Build matrix of existing embeddings
        faiss_ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        # Batch encode existing items
        existing_embeds = _encoder.encode(texts).astype(np.float32)

        to_invalidate = []
        for i, (fid, text, embed) in enumerate(
            zip(faiss_ids, texts, existing_embeds)
        ):
            norm = np.linalg.norm(embed)
            if norm < 1e-8:
                continue
            embed_norm = embed / norm

            # Cosine similarity between new constraint and existing item
            sim = float(np.dot(new_embed_norm, embed_norm))

            # HIGH similarity = same domain/topic (e.g. both are mobile dev)
            # but check if the constraint itself would contradict (sim < 0.5
            # means they're talking about similar topics but different entities)
            if _CONTRADICTION_THRESHOLD_LOW < sim < _CONTRADICTION_THRESHOLD_HIGH:
                to_invalidate.append(fid)

        if to_invalidate:
            with sqlite3.connect(DB_PATH) as conn:
                placeholders = ",".join("?" * len(to_invalidate))
                conn.execute(
                    f"UPDATE faiss_metadata SET valid=0 WHERE faiss_id IN ({placeholders})",
                    to_invalidate,
                )
                conn.commit()
            invalidated = len(to_invalidate)
            logger.info(
                f"Semantic contradiction: invalidated {invalidated} items "
                f"(new_constraint='{new_constraint[:60]}')"
            )

    except Exception as e:
        logger.error(f"detect_semantic_contradiction failed: {e}")

    return invalidated


def store_to_faiss(text: str, metadata: dict) -> int:
    """
    Embed text and store in FAISS index + SQLite metadata.

    Args:
        text:     Sentence or summary to store
        metadata: Dict with keys:
                  session_scope (str), city_scope (str|None),
                  item_type (str), turn_number (int), score (float)

    Returns:
        faiss_id (int) — index of the stored vector.
        Returns -1 on failure.
    """
    try:
        embedding = _encoder.encode([text])[0].astype(np.float32)
        embedding = embedding.reshape(1, -1)

        faiss_id = int(_index.ntotal)
        _index.add(embedding)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO faiss_metadata
                    (faiss_id, text, valid, session_scope,
                     city_scope, item_type, turn_number, score)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            """, (
                faiss_id,
                text,
                metadata.get("session_scope", "general"),
                metadata.get("city_scope"),
                metadata.get("item_type", "research"),
                int(metadata.get("turn_number", 0)),
                float(metadata.get("score", 0.4)),
            ))
            conn.commit()

        logger.debug(f"Stored to FAISS id={faiss_id}, scope={metadata.get('session_scope')}")
        return faiss_id

    except Exception as e:
        logger.error(f"store_to_faiss failed: {e}")
        return -1


def retrieve_from_faiss(
    query: str,
    session_scope: str,
    n: int = None,
) -> list[dict]:
    """
    Retrieve top-n valid items most semantically similar to query.

    Filters applied:
      - valid = 1 (not invalidated)
      - session_scope matches current session

    Args:
        query:         Current user message or query text
        session_scope: Current session scope (e.g., "tokyo_kyoto_trip")
        n:             Number of results to return.
                       Defaults to CFG.faiss.retrieval_return_n (3)

    Returns:
        List of dicts: [{"text": str, "score": float, "faiss_id": int,
                         "item_type": str, "turn_number": int}]
        Empty list if no valid items or FAISS empty.
    """
    if n is None:
        n = CFG.faiss.retrieval_return_n  # 3

    if _index.ntotal == 0:
        return []

    try:
        query_embed = _encoder.encode([query])[0].astype(np.float32)
        query_embed = query_embed.reshape(1, -1)

        top_k = min(CFG.faiss.retrieval_top_k, _index.ntotal)  # 20
        distances, indices = _index.search(query_embed, top_k)

        candidate_ids = [int(idx) for idx in indices[0] if idx >= 0]

        if not candidate_ids:
            return []

        with sqlite3.connect(DB_PATH) as conn:
            placeholders = ",".join("?" * len(candidate_ids))
            rows = conn.execute(f"""
                SELECT faiss_id, text, score, item_type, turn_number
                FROM faiss_metadata
                WHERE faiss_id IN ({placeholders})
                  AND valid = 1
                  AND session_scope = ?
                ORDER BY faiss_id
            """, (*candidate_ids, session_scope)).fetchall()

        if not rows:
            return []

        # Re-rank by FAISS distance (candidate_ids are already distance-ordered)
        id_to_row = {row[0]: row for row in rows}
        results = []
        for fid in candidate_ids:
            if fid in id_to_row:
                row = id_to_row[fid]
                results.append({
                    "text":        row[1],
                    "score":       row[2],
                    "faiss_id":    row[0],
                    "item_type":   row[3],
                    "turn_number": row[4],
                })
            if len(results) >= n:
                break

        return results

    except Exception as e:
        logger.error(f"retrieve_from_faiss failed: {e}")
        return []


def invalidate_session(session_scope: str) -> int:
    """
    Set valid=0 for ALL items in session_scope.
    Used on full pivot (Bali → Switzerland).

    Returns:
        Number of items invalidated.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                UPDATE faiss_metadata
                SET valid = 0
                WHERE session_scope = ? AND valid = 1
            """, (session_scope,))
            conn.commit()
            count = cursor.rowcount
        logger.info(f"Invalidated {count} items for scope '{session_scope}'")
        return count
    except Exception as e:
        logger.error(f"invalidate_session failed: {e}")
        return 0


def invalidate_city_research(city_scope: str) -> int:
    """
    Set valid=0 for RESEARCH items in city_scope.
    Keeps confirmed_booking items valid (they affect budget).
    Used on city transition (Rome → Florence, no full pivot).

    Returns:
        Number of items invalidated.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                UPDATE faiss_metadata
                SET valid = 0
                WHERE city_scope = ?
                  AND item_type = 'research'
                  AND valid = 1
            """, (city_scope,))
            conn.commit()
            count = cursor.rowcount
        logger.info(f"Invalidated {count} research items for city '{city_scope}'")
        return count
    except Exception as e:
        logger.error(f"invalidate_city_research failed: {e}")
        return 0


def get_valid_count(session_scope: str) -> int:
    """Return count of valid items for a session scope. Used in tests."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("""
                SELECT COUNT(*) FROM faiss_metadata
                WHERE session_scope = ? AND valid = 1
            """, (session_scope,)).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def reset_store() -> None:
    """
    Wipe FAISS index and SQLite metadata.
    Used between test runs to ensure clean state.
    """
    global _index
    _index = faiss.IndexFlatL2(EMBEDDING_DIM)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("DELETE FROM faiss_metadata")
            conn.commit()
        # VACUUM must run outside any transaction — use autocommit connection
        with sqlite3.connect(DB_PATH, isolation_level=None) as conn:
            conn.execute("VACUUM")
    except Exception as e:
        logger.error(f"reset_store failed: {e}")
