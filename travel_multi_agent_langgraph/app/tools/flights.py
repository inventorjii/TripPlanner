from ..schemas import FlightResult, FlightOption

async def search_flights(origin: str, destination: str, travelers: int) -> FlightResult:
    return FlightResult(
        origin=origin,
        destination=destination,
        options=[
            FlightOption(airline="DemoAir", flight_number="DA101", departure="08:30", arrival="10:00", price_per_person=6500),
            FlightOption(airline="DemoJet", flight_number="DJ202", departure="13:15", arrival="14:50", price_per_person=5400),
            FlightOption(airline="DemoFly", flight_number="DF303", departure="19:30", arrival="21:10", price_per_person=4800),
        ],
    )
