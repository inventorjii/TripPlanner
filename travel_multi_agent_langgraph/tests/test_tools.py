import asyncio
import pytest
from app.tools.weather import get_weather
from app.tools.flights import search_flights
from app.tools.hotels import search_hotels
from app.tools.traffic import get_traffic

@pytest.mark.asyncio
async def test_provider_tools():
    weather, flights, hotels, traffic = await asyncio.gather(
        get_weather("Goa", "2026-11-10", 3),
        search_flights("Bengaluru", "Goa", 2),
        search_hotels("Goa"),
        get_traffic("Goa", "2026-11-10"),
    )
    assert len(weather.daily_forecast) == 3
    assert flights.options and hotels.options and traffic.routes
