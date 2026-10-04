from unittest.mock import AsyncMock

import pytest

from app.agents import critic_agent, final_agent, research
from app.schemas import BudgetResult, FlightOption, HotelOption, Itinerary
from app.workflow import critic_router


@pytest.mark.asyncio
async def test_research_uses_local_ollama(monkeypatch):
    monkeypatch.setattr("app.agents.call_llm", AsyncMock(return_value="Trip plan summary from local Ollama"))

    state = {"context": type("C", (), {"origin": "Bengaluru", "destination": "Goa", "travelers": 2, "budget": 50000, "start_date": "2026-11-10", "end_date": "2026-11-13", "number_of_days": 3})()}

    result = await research(state)

    assert "research_summary" in result
    assert "Trip plan summary from local Ollama" in result["research_summary"]


@pytest.mark.asyncio
async def test_critic_agent_uses_llm(monkeypatch):
    monkeypatch.setattr("app.agents.call_llm", AsyncMock(return_value="Consider a cheaper hotel for cost control"))

    state = {
        "budget_analysis": type("B", (), {"within_budget": False, "remaining": 1500, "total": 50000})(),
        "itinerary": type("I", (), {"days": [{"day": 1}], "selected_hotel": type("H", (), {"name": "Budget Stay"})(), "selected_flight": type("F", (), {"airline": "Air India", "flight_number": "AI101"})()})(),
    }

    result = await critic_agent(state)

    assert result["critique"].status == "REVISE"
    assert any("Consider a cheaper hotel" in item for item in result["critique"].recommendations)


@pytest.mark.asyncio
async def test_final_agent_uses_llm(monkeypatch):
    monkeypatch.setattr("app.agents.call_llm", AsyncMock(return_value="A polished final travel summary from local Mistral"))

    state = {
        "context": type("C", (), {"origin": "Bengaluru", "destination": "Goa", "travelers": 2, "number_of_days": 3})(),
        "itinerary": Itinerary(
            days=[{"day": 1, "date": "2026-11-10"}],
            selected_flight=FlightOption(
                airline="Air India",
                flight_number="AI101",
                departure="2026-11-10T10:00",
                arrival="2026-11-10T12:30",
                price_per_person=5200,
            ),
            selected_hotel=HotelOption(
                name="Sea View",
                area="North Goa",
                rating=4.8,
                price_per_night=5200,
            ),
        ),
        "budget_analysis": BudgetResult(
            flight_cost=10400,
            hotel_cost=15600,
            local_transport=3500,
            food=10800,
            activities=5000,
            total=45300,
            remaining=4700,
            within_budget=True,
        ),
        "weather": type("W", (), {"summary": "Warm and sunny"})(),
        "traffic": type("T", (), {"summary": "Light traffic"})(),
    }

    result = await final_agent(state)

    assert "A polished final travel summary from local Mistral" in result["final_result"].summary


def test_pass_goes_to_final():
    state = {"critique": type("C", (), {"status":"PASS"})(), "revision_count": 0}
    assert critic_router(state) == "final"


def test_revise_goes_to_revision():
    state = {"critique": type("C", (), {"status":"REVISE"})(), "revision_count": 0}
    assert critic_router(state) == "revise"


def test_revision_is_bounded():
    state = {"critique": type("C", (), {"status":"REVISE"})(), "revision_count": 1}
    assert critic_router(state) == "final"
