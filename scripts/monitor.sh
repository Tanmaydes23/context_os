#!/bin/bash
# Live monitor for data generation pipeline
# Run in a separate tmux pane: bash data_gen/monitor.sh

CHECKPOINT="data_gen/checkpoint.jsonl"
STATS="data_gen/generation_stats.json"
RAW="data_gen/raw_conversations.jsonl"

clear
echo "=================================="
echo "  ContextOS Data Generation Monitor"
echo "=================================="

while true; do
    clear
    echo "=================================="
    echo "  ContextOS Data Generation Monitor"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================="
    echo ""

    # GPU status
    echo "--- GPU STATUS ---"
    nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu,temperature.gpu \
        --format=csv,noheader,nounits 2>/dev/null | \
        awk -F',' '{printf "  GPU: %s\n  VRAM: %s MB used / %s MB free\n  Utilization: %s%%  Temp: %s C\n", $1,$2,$3,$4,$5}'
    echo ""

    # Ollama status
    echo "--- OLLAMA STATUS ---"
    ollama ps 2>/dev/null | head -5 | sed 's/^/  /'
    echo ""

    # Conversation generation progress
    if [ -f "$RAW" ]; then
        CONV_COUNT=$(wc -l < "$RAW")
        echo "--- CONVERSATIONS GENERATED ---"
        echo "  $CONV_COUNT / 500"
        echo "  $(echo "scale=1; $CONV_COUNT * 100 / 500" | bc)% complete"
    else
        echo "--- CONVERSATIONS GENERATED ---"
        echo "  Waiting for first batch..."
    fi
    echo ""

    # Sentence labeling progress
    if [ -f "$CHECKPOINT" ]; then
        TOTAL=$(wc -l < "$CHECKPOINT")
        LABEL1=$(grep -c '"label": 1.0' "$CHECKPOINT" 2>/dev/null || echo 0)
        LABEL0=$(grep -c '"label": 0.0' "$CHECKPOINT" 2>/dev/null || echo 0)
        TIER1=$(grep -c '"tier": 1' "$CHECKPOINT" 2>/dev/null || echo 0)
        TIER2=$(grep -c '"tier": 2' "$CHECKPOINT" 2>/dev/null || echo 0)
        TIER3=$(grep -c '"tier": 3' "$CHECKPOINT" 2>/dev/null || echo 0)
        VERIFIED=$(grep -c '"verified": true' "$CHECKPOINT" 2>/dev/null || echo 0)
        REJECTED=$(grep -c '"verified": false' "$CHECKPOINT" 2>/dev/null || echo 0)

        echo "--- SENTENCE LABELING PROGRESS ---"
        echo "  Total labeled:     $TOTAL"
        echo "  Label=1 (keep):    $LABEL1"
        echo "  Label=0 (drop):    $LABEL0"
        if [ "$TOTAL" -gt 0 ]; then
            echo "  Label=1 rate:      $(echo "scale=2; $LABEL1 * 100 / $TOTAL" | bc)%"
        fi
        echo ""
        echo "--- TIER BREAKDOWN ---"
        echo "  Tier 1 (rules):    $TIER1"
        echo "  Tier 2 (LLM):      $TIER2"
        echo "  Tier 3 (verified): $TIER3"
        echo "  Verify passed:     $VERIFIED"
        echo "  Verify rejected:   $REJECTED (false positives caught)"
    else
        echo "--- SENTENCE LABELING PROGRESS ---"
        echo "  Waiting for first checkpoint..."
    fi
    echo ""

    # Final dataset status
    if [ -f "data_gen/scored_dataset.jsonl" ]; then
        FINAL=$(wc -l < "data_gen/scored_dataset.jsonl")
        echo "--- FINAL DATASET ---"
        echo "  scored_dataset.jsonl: $FINAL rows COMPLETE"
    fi

    echo ""
    echo "  Refreshing every 10s. Ctrl+C to stop monitor."
    sleep 10
done
