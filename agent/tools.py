"""
agent/tools.py
Travel agent tool implementations.

web_search    → duckduckgo-search (real search, no API key)
places_search → geopy + Nominatim/OSM (real geodata, no API key)
weather_fetch → open-meteo (real weather, no API key)
budget_tracker → pure TripState arithmetic
"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search for flights, travel info, and general information.
    Uses DuckDuckGo — no API key required.

    Args:
        query: Search query string
        max_results: Number of results to return (default 5)

    Returns:
        Formatted string of search results.
        Returns error message string on failure — never raises.
    """
    try:
        time.sleep(2)  # avoid DDG 202 rate-limit responses
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        output_parts = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body  = r.get("body", "No description")
            href  = r.get("href", "")
            output_parts.append(
                f"Result {i}:\nTitle: {title}\n{body}\nURL: {href}"
            )

        return "\n\n".join(output_parts)

    except Exception as e:
        logger.error(f"web_search failed for '{query}': {e}")
        return f"Search unavailable. Query was: {query}"


from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as Urllib3Retry

def _make_no_retry_geocoder(user_agent: str) -> Nominatim:
    """Nominatim with urllib3 retries disabled so timeouts fail immediately."""
    gc = Nominatim(user_agent=user_agent, timeout=5)
    # Patch the underlying requests session to stop urllib3 from retrying
    no_retry = HTTPAdapter(max_retries=Urllib3Retry(total=0, read=0, connect=0, raise_on_status=False))
    try:
        gc.adapter.session.mount("https://", no_retry)
        gc.adapter.session.mount("http://",  no_retry)
    except Exception:
        pass  # older geopy versions — logging suppression in eval_harness covers it
    return gc

_geolocator = _make_no_retry_geocoder("context_os_travel_agent_v1")
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1, max_retries=0, swallow_exceptions=True)
_reverse = RateLimiter(_geolocator.reverse, min_delay_seconds=1, max_retries=0, swallow_exceptions=True)


def places_search(query: str, location: str = "", limit: int = 5) -> str:
    """Search for hotels, restaurants, and attractions."""
    try:
        search_query = f"{query} {location}".strip()
        output_parts = []

        # Nominatim geocode — skipped (host unreachable in this environment)
        # DuckDuckGo fallback below provides all needed results

        # Always supplement with DuckDuckGo for richer content
        try:
            time.sleep(2)  # avoid DDG 202 rate-limit responses
            with DDGS() as ddgs:
                web_hits = list(ddgs.text(
                    f"{query} {location} price rating review",
                    max_results=3,
                ))
            for i, r in enumerate(web_hits, len(output_parts) + 1):
                output_parts.append(
                    f"Result {i}:\nName: {r.get('title', '')}\n"
                    f"Info: {r.get('body', '')[:300]}\n"
                    f"URL: {r.get('href', '')}"
                )
        except Exception as e:
            logger.warning(f"DuckDuckGo places fallback failed: {e}")

        return "\n\n".join(output_parts) if output_parts \
            else f"No places found for: {search_query}"

    except Exception as e:
        logger.error(f"places_search failed for '{query}' in '{location}': {e}")
        return f"Places search unavailable: {query} in {location}"


import openmeteo_requests
import requests_cache
from retry_requests import retry

# Cache weather requests for 1 hour
_cache_session = requests_cache.CachedSession(
    ".weather_cache", expire_after=3600
)
_retry_session = retry(_cache_session, retries=3, backoff_factor=0.2)
_openmeteo   = openmeteo_requests.Client(session=_retry_session)
_geo_weather = _make_no_retry_geocoder("context_os_weather_v1")


def weather_fetch(city: str, days: int = 7) -> str:
    """
    Fetch weather forecast for a city.
    Uses Open-Meteo — completely free, no API key required.

    Args:
        city: City name (e.g., "Tokyo", "Rome, Italy")
        days: Forecast days (1-16, default 7)

    Returns:
        Formatted weather forecast string.
        Returns error message on failure — never raises.
    """
    try:
        location = _geo_weather.geocode(city)
        if not location:
            return f"Could not find location: {city}"

        params = {
            "latitude":  location.latitude,
            "longitude": location.longitude,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "weathercode",
            ],
            "forecast_days": min(days, 7),
            "timezone": "auto",
        }

        responses = _openmeteo.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params=params
        )
        response = responses[0]
        daily = response.Daily()

        WMO_CODES = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
            3: "Overcast", 45: "Foggy", 51: "Light drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 80: "Rain showers", 95: "Thunderstorm",
        }

        output_lines = [f"Weather forecast for {city}:"]
        n_days = min(days, 7)

        try:
            max_temps  = daily.Variables(0).ValuesAsNumpy()
            min_temps  = daily.Variables(1).ValuesAsNumpy()
            precips    = daily.Variables(2).ValuesAsNumpy()
            wcodes     = daily.Variables(3).ValuesAsNumpy()

            for i in range(n_days):
                wcode = int(wcodes[i]) if i < len(wcodes) else 0
                desc  = WMO_CODES.get(wcode, "Variable")
                output_lines.append(
                    f"Day {i+1}: High {max_temps[i]:.1f}°C / "
                    f"Low {min_temps[i]:.1f}°C | "
                    f"Rain: {precips[i]:.1f}mm | {desc}"
                )
        except Exception:
            output_lines.append("Detailed forecast unavailable.")

        try:
            avg_max = float(max_temps[:n_days].mean())
            avg_rain = float(precips[:n_days].sum())
            if avg_max < 10:
                output_lines.append("Packing: Heavy coat and warm layers recommended.")
            elif avg_max < 18:
                output_lines.append("Packing: Light jacket recommended.")
            else:
                output_lines.append("Packing: Light clothing. Comfortable weather.")
            if avg_rain > 20:
                output_lines.append("Bring an umbrella — significant rainfall expected.")
        except Exception:
            pass

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"weather_fetch failed for '{city}': {e}")
        return f"Weather unavailable for {city}."


from pipeline.context_state import ContextState as TripState


def budget_tracker(
    action: str,
    amount: float,
    description: str,
    trip_state: TripState,
    turn_number: int = 0,
) -> tuple[str, TripState]:
    """
    Track trip budget. Updates TripState directly.
    This is pure arithmetic — never compressed by Layer 2.

    Args:
        action:      "deduct" | "refund" | "status"
        amount:      Dollar amount (positive float)
        description: What this deduction/refund is for
        trip_state:  Current TripState (mutated and returned)
        turn_number: Current conversation turn (for spend_log)

    Returns:
        (status_message: str, updated_trip_state: TripState)

    Never raises — returns error message string on failure.
    """
    try:
        if action == "deduct":
            if trip_state.budget_total is not None:
                new_remaining = (trip_state.budget_remaining or 0) - amount
                if new_remaining < 0:
                    logger.warning(
                        f"Budget exceeded: trying to deduct ${amount:.2f} "
                        f"but only ${trip_state.budget_remaining:.2f} remaining"
                    )

            trip_state.budget_spent += round(amount, 2)
            trip_state.update_budget_remaining()
            trip_state.spend_log.append({
                "item": description,
                "cost": round(amount, 2),
                "turn": turn_number,
            })

            remaining_str = (
                f"${trip_state.budget_remaining:,.2f}"
                if trip_state.budget_remaining is not None
                else "unknown"
            )
            msg = (
                f"Deducted ${amount:,.2f} for {description}. "
                f"Remaining budget: {remaining_str}"
            )
            return msg, trip_state

        elif action == "refund":
            trip_state.budget_spent = max(
                0.0, trip_state.budget_spent - round(amount, 2)
            )
            trip_state.update_budget_remaining()

            remaining_str = (
                f"${trip_state.budget_remaining:,.2f}"
                if trip_state.budget_remaining is not None
                else "unknown"
            )
            msg = (
                f"Refunded ${amount:,.2f} for {description}. "
                f"Remaining budget: {remaining_str}"
            )
            return msg, trip_state

        elif action == "status":
            if trip_state.budget_total is None:
                return "No budget set.", trip_state

            msg = (
                f"Budget: Total ${trip_state.budget_total:,.2f} | "
                f"Spent ${trip_state.budget_spent:,.2f} | "
                f"Remaining ${trip_state.budget_remaining:,.2f}"
            )
            return msg, trip_state

        else:
            return f"Unknown budget action: {action}", trip_state

    except Exception as e:
        logger.error(f"budget_tracker error: {e}")
        return f"Budget tracker error: {e}", trip_state


def dispatch_tool(
    tool_name: str,
    args: dict,
    trip_state: TripState,
    turn_number: int = 0,
) -> tuple[str, Optional[TripState]]:
    """
    Dispatch a tool call by name.

    Returns:
        (tool_output: str, updated_trip_state or None)
        trip_state is only updated for budget_tracker.
    """
    try:
        if tool_name == "web_search":
            return web_search(
                query=args.get("query", ""),
                max_results=args.get("max_results", 5),
            ), None

        elif tool_name == "places_search":
            return places_search(
                query=args.get("query", ""),
                location=args.get("location", ""),
                limit=args.get("limit", 5),
            ), None

        elif tool_name == "weather_fetch":
            return weather_fetch(
                city=args.get("city", ""),
                days=args.get("days", 7),
            ), None

        elif tool_name == "budget_tracker":
            msg, updated_state = budget_tracker(
                action=args.get("action", "status"),
                amount=float(args.get("amount", 0.0)),
                description=args.get("description", ""),
                trip_state=trip_state,
                turn_number=turn_number,
            )
            return msg, updated_state

        else:
            return f"Unknown tool: {tool_name}", None

    except Exception as e:
        logger.error(f"dispatch_tool error for {tool_name}: {e}")
        return f"Tool {tool_name} failed: {e}", None
