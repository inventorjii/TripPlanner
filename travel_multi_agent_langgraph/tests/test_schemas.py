from app.schemas import TripRequest

def test_trip_request():
    request = TripRequest(
        origin="Bengaluru", destination="Goa",
        start_date="2026-11-10", end_date="2026-11-13",
        travelers=2, budget=45000,
    )
    assert request.travelers == 2
    assert request.budget == 45000
