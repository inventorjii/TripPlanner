import logging
from pathlib import Path
from datetime import date
from ollama import AsyncClient
from .config import get_settings
from .state import TripState
from .schemas import TripContext, Plan, Itinerary, BudgetResult, Critique, FinalResult
from .tools.weather import get_weather
from .tools.flights import search_flights
from .tools.hotels import search_hotels
from .tools.traffic import get_traffic

LOG_FILE = Path(__file__).resolve().parent.parent / "travel_agent_debug.txt"
logger = logging.getLogger("travel-agent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(file_handler)


def _safe_log(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _safe_log(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_log(v) for v in value]
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return str(value)


def _log_agent_step(agent_name: str, state: dict, result: dict | None = None):
    logger.info("AGENT_START | %s | input=%s", agent_name, _safe_log(state))
    if result is not None:
        logger.info("AGENT_END | %s | output=%s", agent_name, _safe_log(result))


async def call_llm(prompt: str, system_prompt: str = "You are a careful travel-planning assistant.") -> str:
    logger.info("LLM_CALL | prompt=%s", prompt[:500])
    client = AsyncClient(host=get_settings().ollama_base_url)
    response = await client.chat(
        model=get_settings().ollama_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.3},
    )
    text = response["message"]["content"].strip()
    logger.info("LLM_RESPONSE | response=%s", text[:500])
    return text

async def planner(state: TripState):
    req = state["request"]
    logger.info("planner: starting trip planning for %s -> %s", req["origin"], req["destination"])
    start = date.fromisoformat(req["start_date"])
    end = date.fromisoformat(req["end_date"])
    days = (end - start).days
    if days <= 0:
        logger.error("planner: invalid trip window %s -> %s", req["start_date"], req["end_date"])
        raise ValueError("end_date must be after start_date")
    context = TripContext(
        origin=req["origin"], destination=req["destination"],
        start_date=req["start_date"], end_date=req["end_date"],
        travelers=req["travelers"], budget=req["budget"], number_of_days=days,
    )
    plan = Plan(
        objective=f"Create a {days}-day trip from {req['origin']} to {req['destination']}.",
        required_research=["weather","flights","hotels","traffic"],
    )
    result = {"context": context, "plan": plan, "revision_count": 0}
    logger.info("planner: created trip context and plan for %s days", days)
    _log_agent_step("planner", state, result)
    return result

async def research(state: TripState):
    c = state["context"]
    logger.info("research: contacting Ollama for trip research on %s -> %s", c.origin, c.destination)
    prompt = (
        f"Create a concise trip research brief for a trip from {c.origin} to {c.destination} "
        f"from {c.start_date} to {c.end_date} for {c.travelers} travelers with a budget of {c.budget}. "
        "Include practical notes on weather expectations, likely travel timing, hotel area considerations, and budget-focused recommendations."
    )
    try:
        summary = await call_llm(prompt)
        logger.info("research: Ollama research summary received")
    except Exception as exc:
        logger.warning("research: Ollama failed, falling back to default summary: %s", exc)
        summary = (
            f"Local Ollama model is unavailable at {get_settings().ollama_base_url}. "
            f"Use standard travel planning guidance for {c.destination}, focusing on weather patterns, "
            "budget-conscious lodging, and flexible day plans."
        )
    result = {"research_summary": summary}
    _log_agent_step("research", state, result)
    return result

async def weather_agent(state: TripState):
    c = state["context"]
    logger.info("weather_agent: fetching weather for %s (%s days)", c.destination, c.number_of_days)
    weather = await get_weather(c.destination, c.start_date, c.number_of_days)
    result = {"weather": weather}
    logger.info("weather_agent: weather data received for %s", c.destination)
    _log_agent_step("weather_agent", state, result)
    return result

async def flight_agent(state: TripState):
    c = state["context"]
    logger.info("flight_agent: searching flights from %s to %s", c.origin, c.destination)
    flights = await search_flights(c.origin, c.destination, c.travelers)
    result = {"flights": flights}
    logger.info("flight_agent: %s flight options returned", len(flights.options))
    _log_agent_step("flight_agent", state, result)
    return result

async def hotel_agent(state: TripState):
    c = state["context"]
    logger.info("hotel_agent: searching hotels in %s", c.destination)
    hotels = await search_hotels(c.destination)
    result = {"hotels": hotels}
    logger.info("hotel_agent: %s hotel options returned", len(hotels.options))
    _log_agent_step("hotel_agent", state, result)
    return result

async def traffic_agent(state: TripState):
    c = state["context"]
    logger.info("traffic_agent: fetching traffic summary for %s on %s", c.destination, c.start_date)
    traffic = await get_traffic(c.destination, c.start_date)
    result = {"traffic": traffic}
    logger.info("traffic_agent: traffic summary received")
    _log_agent_step("traffic_agent", state, result)
    return result

async def itinerary_agent(state: TripState):
    c = state["context"]
    flights = state["flights"]
    hotels = state["hotels"]
    weather = state["weather"]
    logger.info("itinerary_agent: building itinerary from %s flight options and %s hotel options", len(flights.options), len(hotels.options))

    selected_flight = min(flights.options, key=lambda x: x.price_per_person)
    selected_hotel = max(hotels.options, key=lambda x: (x.rating, -x.price_per_night))

    days = []
    for i, forecast in enumerate(weather.daily_forecast, 1):
        activity = "Outdoor sightseeing" if forecast["rain_probability"] < 40 else "Indoor/local activities"
        days.append({
            "day": i,
            "date": forecast["date"],
            "weather": forecast,
            "morning": activity,
            "afternoon": activity,
            "evening": "Dinner and relaxed local exploration",
        })

    itinerary = Itinerary(days=days, selected_flight=selected_flight, selected_hotel=selected_hotel)
    result = {"itinerary": itinerary}
    logger.info("itinerary_agent: selected flight=%s %s and hotel=%s", selected_flight.airline, selected_flight.flight_number, selected_hotel.name)
    _log_agent_step("itinerary_agent", state, result)
    return result

async def budget_agent(state: TripState):
    c = state["context"]
    itinerary = state["itinerary"]
    logger.info("budget_agent: calculating trip cost for %s travelers", c.travelers)
    flight_cost = itinerary.selected_flight.price_per_person * c.travelers
    hotel_cost = itinerary.selected_hotel.price_per_night * c.number_of_days
    local_transport = 3500
    food = 1800 * c.travelers * c.number_of_days
    activities = 2500 * c.travelers
    total = flight_cost + hotel_cost + local_transport + food + activities
    budget = BudgetResult(
        flight_cost=flight_cost, hotel_cost=hotel_cost,
        local_transport=local_transport, food=food, activities=activities,
        total=total, remaining=c.budget-total, within_budget=total <= c.budget,
    )
    result = {"budget_analysis": budget}
    logger.info("budget_agent: total=%s budget=%s within_budget=%s", total, c.budget, budget.within_budget)
    _log_agent_step("budget_agent", state, result)
    return result

async def critic_agent(state: TripState):
    budget = state["budget_analysis"]
    itinerary = state["itinerary"]
    issues, recommendations = [], []
    logger.info("critic_agent: reviewing budget and itinerary quality")
    if not budget.within_budget:
        issues.append(f"Trip exceeds budget by {abs(budget.remaining):.2f}.")
        recommendations.append("Select a cheaper hotel and/or flight.")
    if not itinerary.days:
        issues.append("Itinerary contains no activities.")

    try:
        llm_feedback = await call_llm(
            f"Review this travel plan and suggest improvements. Budget: {budget.total}. "
            f"Hotel: {itinerary.selected_hotel.name}. Flight: {itinerary.selected_flight.airline}. "
            f"Days: {len(itinerary.days)}. Keep output brief and actionable."
        )
        if llm_feedback:
            recommendations.append(llm_feedback[:300])
            logger.info("critic_agent: LLM feedback added")
    except Exception as exc:
        logger.warning("critic_agent: LLM critique unavailable: %s", exc)

    critique = Critique(
        status="PASS" if not issues else "REVISE",
        issues=issues,
        recommendations=recommendations,
    )
    result = {"critique": critique}
    logger.info("critic_agent: critique status=%s issues=%s", critique.status, critique.issues)
    _log_agent_step("critic_agent", state, result)
    return result

async def revision_node(state: TripState):
    revision_count = state.get("revision_count", 0) + 1
    result = {"revision_count": revision_count}
    logger.info("revision_node: revision_count=%s", revision_count)
    _log_agent_step("revision_node", state, result)
    return result

async def final_agent(state: TripState):
    c = state["context"]
    itinerary = state["itinerary"]
    logger.info("final_agent: preparing final trip summary for %s -> %s", c.origin, c.destination)
    try:
        summary = await call_llm(
            f"Write a polished final summary for a {c.number_of_days}-day trip from {c.origin} to {c.destination} "
            f"for {c.travelers} traveler(s). Include the best flight, hotel, weather, and budget highlights. "
            f"Flight: {itinerary.selected_flight.airline} {itinerary.selected_flight.flight_number}. "
            f"Hotel: {itinerary.selected_hotel.name}."
        )
        logger.info("final_agent: LLM summary generated")
    except Exception as exc:
        logger.warning("final_agent: LLM summary unavailable, using fallback: %s", exc)
        summary = f"{c.number_of_days}-day trip from {c.origin} to {c.destination} for {c.travelers} traveler(s)."
    final_result = FinalResult(
        summary=summary,
        itinerary=state["itinerary"],
        budget=state["budget_analysis"],
        weather_summary=state["weather"].summary,
        traffic_summary=state["traffic"].summary,
        notes=["Flight, hotel, weather and traffic data are mock provider results.",
               "Verify live availability before booking."],
    )
    result = {"final_result": final_result}
    logger.info("final_agent: final result created")
    _log_agent_step("final_agent", state, result)
    return result
