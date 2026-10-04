from typing import TypedDict
from .schemas import TripContext, Plan, WeatherResult, FlightResult, HotelResult, TrafficResult, Itinerary, BudgetResult, Critique, FinalResult

class TripState(TypedDict, total=False):
    request: dict
    context: TripContext
    plan: Plan
    weather: WeatherResult
    flights: FlightResult
    hotels: HotelResult
    traffic: TrafficResult
    itinerary: Itinerary
    budget_analysis: BudgetResult
    critique: Critique
    final_result: FinalResult
    revision_count: int
