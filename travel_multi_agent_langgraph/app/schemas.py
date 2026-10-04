from typing import Literal
from pydantic import BaseModel, Field

class TripRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    start_date: str
    end_date: str
    travelers: int = Field(ge=1, le=20)
    budget: float = Field(gt=0)

class TripContext(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    travelers: int
    budget: float
    number_of_days: int

class Plan(BaseModel):
    objective: str
    required_research: list[str]

class WeatherResult(BaseModel):
    destination: str
    daily_forecast: list[dict]
    summary: str

class FlightOption(BaseModel):
    airline: str
    flight_number: str
    departure: str
    arrival: str
    price_per_person: float

class FlightResult(BaseModel):
    origin: str
    destination: str
    options: list[FlightOption]

class HotelOption(BaseModel):
    name: str
    area: str
    rating: float
    price_per_night: float

class HotelResult(BaseModel):
    destination: str
    options: list[HotelOption]

class TrafficResult(BaseModel):
    routes: list[dict]
    summary: str

class Itinerary(BaseModel):
    days: list[dict]
    selected_flight: FlightOption
    selected_hotel: HotelOption

class BudgetResult(BaseModel):
    flight_cost: float
    hotel_cost: float
    local_transport: float
    food: float
    activities: float
    total: float
    remaining: float
    within_budget: bool

class Critique(BaseModel):
    status: Literal["PASS", "REVISE"]
    issues: list[str]
    recommendations: list[str]

class FinalResult(BaseModel):
    summary: str
    itinerary: Itinerary
    budget: BudgetResult
    weather_summary: str
    traffic_summary: str
    notes: list[str]

class TripResponse(BaseModel):
    thread_id: str
    status: str
    result: FinalResult
