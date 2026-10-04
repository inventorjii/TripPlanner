from ..schemas import TrafficResult

async def get_traffic(destination: str, start_date: str) -> TrafficResult:
    return TrafficResult(
        routes=[
            {"route":"Airport -> Hotel","normal_minutes":35,"peak_minutes":65,"traffic":"moderate"},
            {"route":"Hotel -> Main Attractions","normal_minutes":20,"peak_minutes":40,"traffic":"light"},
        ],
        summary="Airport transfer may take longer during peak hours.",
    )
