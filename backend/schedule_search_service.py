"""
ScheduleSearchService – Középső szintű menetrend-kereső komponens
=================================================================
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TripRepository(Protocol):
    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
        departure_time_from: str | None = None,
    ) -> list[dict]:
        ...


class ScheduleSearchService:
    MAX_RESULTS = 5

    def __init__(self, repository: TripRepository):
        self._repo = repository

    def search(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str] | None = None,
        departure_time_from: str | None = None,
    ) -> dict:
        if not origin or not origin.strip():
            raise ValueError("Az indulási hely nem lehet üres.")
        if not destination or not destination.strip():
            raise ValueError("A cél nem lehet üres.")

        modes = transport_modes or []

        # Adatlekérés a repository rétegből
        raw_trips = self._repo.find_trips(
            origin.strip(),
            destination.strip(),
            modes,
            departure_time_from,
        )

        total_found = len(raw_trips)

        # Üzleti logika: rendezés indulási idő szerint
        sorted_trips = sorted(raw_trips, key=lambda t: t.get("departure_time") or "")

        # Max. 5 találat visszaadása
        limited = sorted_trips[: self.MAX_RESULTS]

        return {
            "success": True,
            "results": limited,
            "total_found": total_found,
        }
