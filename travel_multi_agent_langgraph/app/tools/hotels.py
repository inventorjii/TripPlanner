from ..schemas import HotelResult, HotelOption

async def search_hotels(destination: str) -> HotelResult:
    return HotelResult(
        destination=destination,
        options=[
            HotelOption(name="Demo Beach Resort", area="Beach Road", rating=4.5, price_per_night=5200),
            HotelOption(name="Demo Central Hotel", area="Central", rating=4.2, price_per_night=3900),
            HotelOption(name="Demo Budget Stay", area="Old Town", rating=3.9, price_per_night=2500),
        ],
    )
