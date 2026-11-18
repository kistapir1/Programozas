"""
ScheduleSearchService – Középső szintű menetrend-kereső komponens
=================================================================
Közvetlen és átszállásos útvonalak egységes kezelése, akadálymentességi és kerékpáros szűréssel.
"""

import inspect
from typing import Protocol, runtime_checkable


def time_to_seconds(t: str) -> int:
    """Időpont konvertálása másodpercre."""
    if not t:
        return 0
    parts = t.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


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
        max_transfers: int = 2,
        min_transfer_time: int = 5,
        bikes_allowed: bool = False,
        wheelchair_accessible: bool = False,
        wheelchair_boarding: bool = False,
    ) -> dict:
        if not origin or not origin.strip():
            raise ValueError("Az indulási hely nem lehet üres.")
        if not destination or not destination.strip():
            raise ValueError("A cél nem lehet üres.")

        modes = transport_modes or []

        # 1. Közvetlen járatok lekérése a repository rétegből
        # Ellenőrizzük a repository metódusának paramétereit (kompatibilitás a stub tesztekkel)
        sig = inspect.signature(self._repo.find_trips)
        kwargs = {}
        if "bikes_allowed" in sig.parameters:
            kwargs["bikes_allowed"] = bikes_allowed
        if "wheelchair_accessible" in sig.parameters:
            kwargs["wheelchair_accessible"] = wheelchair_accessible
        if "wheelchair_boarding" in sig.parameters:
            kwargs["wheelchair_boarding"] = wheelchair_boarding

        raw_direct = self._repo.find_trips(
            origin.strip(),
            destination.strip(),
            modes,
            departure_time_from,
            **kwargs,
        )

        direct_journeys: list[dict] = []
        for t in raw_direct:
            j = dict(t)
            j["transfers"] = 0
            if "legs" not in j:
                j["legs"] = [
                    {
                        "route_short_name": t.get("route_short_name", ""),
                        "route_long_name": t.get("route_long_name", ""),
                        "transport_mode": t.get("transport_mode", ""),
                        "operator": t.get("operator", ""),
                        "origin_station": t.get("origin_station", ""),
                        "departure_time": t.get("departure_time", ""),
                        "destination_station": t.get("destination_station", ""),
                        "arrival_time": t.get("arrival_time", ""),
                        "bikes_allowed": t.get("bikes_allowed", 0),
                        "wheelchair_accessible": t.get("wheelchair_accessible", 0),
                    }
                ]
            direct_journeys.append(j)

        all_journeys: list[dict] = list(direct_journeys)

        # 2. Átszállásos járatok keresése, ha a felhasználó engedélyezte
        if max_transfers >= 1 and hasattr(self._repo, "find_transfer_trips"):
            try:
                min_transfer_sec = max(0, min(60, min_transfer_time)) * 60
                transfer_journeys = self._repo.find_transfer_trips(
                    origin.strip(),
                    destination.strip(),
                    modes,
                    departure_time_from,
                    max_transfers=max_transfers,
                    min_transfer_seconds=min_transfer_sec,
                    bikes_allowed=bikes_allowed,
                    wheelchair_accessible=wheelchair_accessible,
                    wheelchair_boarding=wheelchair_boarding,
                )
                all_journeys.extend(transfer_journeys)
            except Exception as e:
                print(f"[!] Hiba az átszállásos keresés közben: {e}")

        total_found = len(all_journeys)

        # 3. Intelligens rendezés
        ref_sec = time_to_seconds(departure_time_from) if departure_time_from else 0

        def calculate_journey_sort_key(journey: dict):
            dep_str = journey.get("departure_time") or "00:00:00"
            arr_str = journey.get("arrival_time") or "00:00:00"
            dep_sec = time_to_seconds(dep_str)
            arr_sec = time_to_seconds(arr_str)

            if departure_time_from and dep_sec < ref_sec:
                dep_sec += 24 * 3600

            if arr_sec < dep_sec:
                arr_sec += 24 * 3600

            arrival_offset = arr_sec - ref_sec
            transfers = journey.get("transfers", 0)
            return (arrival_offset, transfers, dep_sec)

        if max_transfers == 0:
            sorted_journeys = sorted(
                all_journeys,
                key=lambda t: (
                    time_to_seconds(t.get("departure_time") or "") + (24 * 3600 if departure_time_from and time_to_seconds(t.get("departure_time") or "") < ref_sec else 0)
                ),
            )
        else:
            sorted_journeys = sorted(all_journeys, key=calculate_journey_sort_key)

        limited = sorted_journeys[: self.MAX_RESULTS]

        return {
            "success": True,
            "results": limited,
            "total_found": total_found,
        }
