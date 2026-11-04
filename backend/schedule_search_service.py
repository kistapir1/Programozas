"""
ScheduleSearchService – Középső szintű menetrend-kereső komponens
=================================================================

Ez a komponens a menetrend-kereső alkalmazás középső (business logic) rétege:
  - HASZNÁLJA:  TripRepository (adatbázis vagy stub) – az alatta lévő réteg
  - HASZNÁLJA:  az API végpont és az integrációs teszt driverek – a felette lévő réteg
"""

from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Interfész (Protocol) – ezt implementálja a valódi DB repo és a stub is
# ---------------------------------------------------------------------------

@runtime_checkable
class TripRepository(Protocol):
    """
    Az adatforrás absztrakciója.
    A valódi implementáció PostgreSQL-ből olvas, a stub beégetett adatot ad.
    """

    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
    ) -> list[dict]:
        """
        Visszaadja az origin → destination útvonalhoz tartozó járatokat.
        Minden elem dict:
          trip_id, route_short_name, route_long_name, transport_mode,
          operator, origin_station, departure_time, destination_station, arrival_time
        """
        ...


# ---------------------------------------------------------------------------
# A tényleges középső komponens
# ---------------------------------------------------------------------------

class ScheduleSearchService:
    """
    Menetrend-kereső szolgáltatás.

    Középső réteg:
      - Fogadja a keresési paramétereket (indulási hely, cél, közlekedési mód)
      - Delegál egy TripRepository-nak az adatok lekéréséhez
      - Végrehajtja az üzleti logikát: időrend szerinti rendezés, max. 5 találat

    Függőséget (TripRepository) kívülről kapja → könnyen tesztelhető stub-bal.
    """

    MAX_RESULTS = 5

    def __init__(self, repository: TripRepository):
        self._repo = repository

    def search(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str] | None = None,
    ) -> dict:
        """
        Menetrend keresés végrehajtása.

        Args:
            origin:          Indulási helyszín neve (részleges egyezés)
            destination:     Cél helyszín neve (részleges egyezés)
            transport_modes: Szűrő lista, pl. ['train', 'intercity_bus'].
                             Ha üres vagy None → minden mód szerepel.

        Returns:
            {
              'success': bool,
              'results': list[dict],   # max. MAX_RESULTS elem, dep_time szerint rendezve
              'total_found': int,      # szűrés előtti egyezések száma
            }

        Raises:
            ValueError: ha origin vagy destination üres string.
        """
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
