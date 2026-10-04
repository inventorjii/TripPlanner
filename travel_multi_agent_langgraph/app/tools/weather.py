from datetime import date, timedelta
from ..schemas import WeatherResult

async def get_weather(destination: str, start_date: str, days: int) -> WeatherResult:
    start = date.fromisoformat(start_date)
    forecast = []
    for i in range(days):
        current = start + timedelta(days=i)
        forecast.append({
            "date": current.isoformat(),
            "temperature_c": 27 + i % 3,
            "rain_probability": [20, 35, 15, 25, 40][i % 5],
        })
    return WeatherResult(
        destination=destination,
        daily_forecast=forecast,
        summary="Mostly suitable weather; carry a light rain jacket.",
    )
