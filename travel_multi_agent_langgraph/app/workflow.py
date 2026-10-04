from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .state import TripState
from .agents import planner, research, weather_agent, flight_agent, hotel_agent, traffic_agent, itinerary_agent, budget_agent, critic_agent, revision_node, final_agent

def critic_router(state: TripState):
    if state["critique"].status == "PASS":
        return "final"
    if state.get("revision_count", 0) >= 1:
        return "final"
    return "revise"

def build_workflow(checkpointer: AsyncPostgresSaver | None = None):
    builder = StateGraph(TripState)

    for name, fn in [
        ("planner", planner), ("research", research),
        ("weather", weather_agent), ("flight", flight_agent),
        ("hotel", hotel_agent), ("traffic", traffic_agent),
        ("itinerary", itinerary_agent), ("budget", budget_agent),
        ("critic", critic_agent), ("revision", revision_node),
        ("final", final_agent),
    ]:
        builder.add_node(name, fn)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "research")

    # Parallel fan-out.
    builder.add_edge("research", "weather")
    builder.add_edge("research", "flight")
    builder.add_edge("research", "hotel")
    builder.add_edge("research", "traffic")

    # Fan-in. Itinerary waits for all four branches.
    builder.add_edge("weather", "itinerary")
    builder.add_edge("flight", "itinerary")
    builder.add_edge("hotel", "itinerary")
    builder.add_edge("traffic", "itinerary")

    builder.add_edge("itinerary", "budget")
    builder.add_edge("budget", "critic")

    builder.add_conditional_edges(
        "critic",
        critic_router,
        {"revise": "revision", "final": "final"},
    )
    builder.add_edge("revision", "itinerary")
    builder.add_edge("final", END)

    if checkpointer is None:
        return builder.compile()
    return builder.compile(checkpointer=checkpointer)
