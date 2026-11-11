"""
test_integration.py – Integrációs teszt a ScheduleSearchService-hez
====================================================================

STUB:   StubTripRepository – beégetett menetrend-adatokat ad vissza
        (nem kell élő adatbázis-kapcsolat a teszthez)

DRIVER: run_driver() – különböző keresési paraméterekkel hívja a service-t,
        összehasonlítja az elvárt és kapott eredményt, kiírja az eredményt.

A feladat analógiájára:
  Rendelés végösszeg → Menetrend keresés (útvonal + szűrők)
  Egyes tételek ára  → Menetrendek adatai (stub adja vissza)
  Tétel lista        → Keresési paraméterek (origin, destination, modes)
"""

from schedule_search_service import ScheduleSearchService

# =============================================================================
# STUB – beégetett adatok, nem kell valódi DB
# =============================================================================

class StubTripRepository:
    """
    Stub implementáció a TripRepository protokollhoz.

    Szabály (a feladatban kért analógia szerint):
      - Ha az origin tartalmazza 'Győr'-t  → a megfelelő győri járatokat adja vissza
      - Ha az origin tartalmazza 'Budapest'-et → a budapesti indulású járatokat adja vissza
      - Minden más origin → üres lista (nincs találat)

    A transport_modes szűrőt a stub maga alkalmazza a beégetett listán.
    """

    # Beégetett menetrend-adatok (a valódi DB tartalma alapján)
    _ALL_TRIPS: list[dict] = [
        # --- Győr → Sopron (vonat) ---
        {
            "trip_id": 1,
            "route_short_name": "IC 934",
            "route_long_name": "Budapest - Győr - Sopron (InterCity)",
            "transport_mode": "train",
            "operator": "MÁV-START",
            "origin_station": "Győr vasútállomás",
            "departure_time": "08:21:00",
            "destination_station": "Sopron vasútállomás",
            "arrival_time": "09:25:00",
        },
        # --- Győr → Veszprém (helyközi busz) ---
        {
            "trip_id": 2,
            "route_short_name": "7020",
            "route_long_name": "Győr - Veszprém helyközi autóbusz",
            "transport_mode": "intercity_bus",
            "operator": "Volánbusz",
            "origin_station": "Győr autóbusz-állomás",
            "departure_time": "10:00:00",
            "destination_station": "Veszprém autóbusz-állomás",
            "arrival_time": "11:25:00",
        },
        # --- Budapest → Győr (több vonat – a 20 elemű teszt feltöltéséhez) ---
        *[
            {
                "trip_id": 100 + i,
                "route_short_name": f"S{10 + i}",
                "route_long_name": "Budapest - Tatabánya - Győr (Személyvonat)",
                "transport_mode": "train",
                "operator": "MÁV-START",
                "origin_station": "Budapest-Keleti",
                "departure_time": f"{5 + i:02d}:00:00",
                "destination_station": "Győr vasútállomás",
                "arrival_time": f"{6 + i:02d}:30:00",
            }
            for i in range(20)   # 20 Budapest→Győr vonat
        ],
        # --- Budapest → Győr (intercity busz is van néhány) ---
        *[
            {
                "trip_id": 200 + i,
                "route_short_name": f"BUS-{i}",
                "route_long_name": "Budapest Népliget - Győr autóbusz",
                "transport_mode": "intercity_bus",
                "operator": "Volánbusz",
                "origin_station": "Budapest Népliget autóbusz-pályaudvar",
                "departure_time": f"{7 + i:02d}:30:00",
                "destination_station": "Győr autóbusz-állomás",
                "arrival_time": f"{9 + i:02d}:15:00",
            }
            for i in range(5)
        ],
    ]

    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
        departure_time_from: str | None = None,
    ) -> list[dict]:
        """Beégetett adatokon keres, origin/destination részleges egyezéssel."""
        origin_lower = origin.lower()
        dest_lower   = destination.lower()

        matches = [
            t for t in self._ALL_TRIPS
            if origin_lower in t["origin_station"].lower()
            and dest_lower  in t["destination_station"].lower()
        ]

        # Transport mode szűrő alkalmazása (ha van)
        if transport_modes:
            matches = [t for t in matches if t["transport_mode"] in transport_modes]

        return matches


# =============================================================================
# DRIVER segédfüggvény
# =============================================================================

def run_driver(
    driver_name: str,
    origin: str,
    destination: str,
    transport_modes: list[str],
    expected_count: int,
    expected_first_route: str | None = None,
):
    """
    Egy teszt-eset futtatása.

    Args:
        driver_name:         A teszt neve (leírás)
        origin:              Keresett indulási hely
        destination:         Keresett cél
        transport_modes:     Közlekedési mód szűrő
        expected_count:      Elvárt találatok száma (0..5)
        expected_first_route: Az első találat elvárt route_short_name-je (vagy None)
    """
    stub = StubTripRepository()
    service = ScheduleSearchService(stub)

    try:
        result = service.search(origin, destination, transport_modes)
    except ValueError as e:
        # Pl. üres origin → ValueError várható
        actual_count = -1          # speciális jelzés: kivétel dobódott
        result = {"results": [], "total_found": 0}
        error_msg = str(e)
    else:
        actual_count = len(result["results"])
        error_msg = None

    # Értékelés
    count_ok = (actual_count == expected_count)

    route_ok = True
    if expected_first_route is not None and actual_count > 0:
        got_route = result["results"][0].get("route_short_name", "")
        route_ok = (got_route == expected_first_route)

    passed = count_ok and route_ok

    # Kimenet
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{'─' * 60}")
    print(f"  {status}  |  {driver_name}")
    print(f"  Paraméterek : origin='{origin}', dest='{destination}', modes={transport_modes or 'mind'}")
    if error_msg:
        print(f"  Kivétel     : {error_msg}")
        print(f"  Elvárt db   : {expected_count}  |  Kapott db: {actual_count} (kivétel → -1)")
    else:
        print(f"  Elvárt db   : {expected_count}  |  Kapott db: {actual_count}  {'✓' if count_ok else '✗'}")
        if expected_first_route:
            got = result["results"][0].get("route_short_name", "–") if actual_count > 0 else "–"
            print(f"  Elvárt járat: '{expected_first_route}'  |  Kapott: '{got}'  {'✓' if route_ok else '✗'}")
        if result["results"]:
            print(f"  Találatok   :")
            for r in result["results"]:
                print(f"    [{r['route_short_name']}] {r['origin_station']} {r['departure_time']} → "
                      f"{r['destination_station']} {r['arrival_time']}  ({r['transport_mode']})")
    return passed


# =============================================================================
# DRIVEREK – különböző adatokkal
# =============================================================================

def main():
    print("=" * 60)
    print("  INTEGRÁCIÓS TESZT – ScheduleSearchService")
    print("  Stub: StubTripRepository (nincs élő DB)")
    print("=" * 60)

    results: list[bool] = []

    # ── Driver 1: Üres origin → ValueError ──────────────────────────
    results.append(run_driver(
        driver_name        = "1. Üres indulási hely → ValueError kivétel",
        origin             = "",
        destination        = "Sopron",
        transport_modes    = [],
        expected_count     = -1,   # -1 = kivételt várunk
    ))

    # ── Driver 2: Üres destination → ValueError ──────────────────────
    results.append(run_driver(
        driver_name        = "2. Üres cél → ValueError kivétel",
        origin             = "Győr",
        destination        = "",
        transport_modes    = [],
        expected_count     = -1,
    ))

    # ── Driver 3: Ismeretlen útvonal → 0 találat ─────────────────────
    results.append(run_driver(
        driver_name        = "3. Ismeretlen útvonal → 0 találat",
        origin             = "Debrecen",
        destination        = "Pécs",
        transport_modes    = [],
        expected_count     = 0,
    ))

    # ── Driver 4: Győr → Sopron, minden mód → 1 találat ─────────────
    results.append(run_driver(
        driver_name        = "4. Győr → Sopron (minden mód) → 1 találat",
        origin             = "Győr",
        destination        = "Sopron",
        transport_modes    = [],
        expected_count     = 1,
        expected_first_route = "IC 934",
    ))

    # ── Driver 5: Győr → Sopron, csak vonat → 1 találat ─────────────
    results.append(run_driver(
        driver_name        = "5. Győr → Sopron, csak vonat → 1 találat",
        origin             = "Győr",
        destination        = "Sopron",
        transport_modes    = ["train"],
        expected_count     = 1,
        expected_first_route = "IC 934",
    ))

    # ── Driver 6: Győr → Sopron, csak busz → 0 találat ──────────────
    results.append(run_driver(
        driver_name        = "6. Győr → Sopron, csak intercity_bus → 0 találat",
        origin             = "Győr",
        destination        = "Sopron",
        transport_modes    = ["intercity_bus"],
        expected_count     = 0,
    ))

    # ── Driver 7: Győr → Veszprém, minden mód → 1 találat ───────────
    results.append(run_driver(
        driver_name        = "7. Győr → Veszprém (minden mód) → 1 találat",
        origin             = "Győr",
        destination        = "Veszprém",
        transport_modes    = [],
        expected_count     = 1,
        expected_first_route = "7020",
    ))

    # ── Driver 8: Budapest → Győr, minden mód → LIMIT=5 ─────────────
    # A stubban 20 vonat + 5 busz = 25 Budapest→Győr járat van
    # A service max 5-öt ad vissza, időrendben
    results.append(run_driver(
        driver_name        = "8. Budapest → Győr (25 járat a stubban) → max 5 találat (LIMIT teszt)",
        origin             = "Budapest",
        destination        = "Győr",
        transport_modes    = [],
        expected_count     = 5,
        expected_first_route = "S10",   # a legkorábbi indulású vonat (05:00)
    ))

    # ── Driver 9: Budapest → Győr, csak vonat → 5 találat ───────────
    results.append(run_driver(
        driver_name        = "9. Budapest → Győr, csak vonat (20 van) → max 5 találat",
        origin             = "Budapest",
        destination        = "Győr",
        transport_modes    = ["train"],
        expected_count     = 5,
    ))

    # ── Driver 10: Budapest → Győr, csak busz → 5 találat ───────────
    # Pontosan 5 busz van → mind visszajön
    results.append(run_driver(
        driver_name        = "10. Budapest → Győr, csak intercity_bus (5 van) → 5 találat",
        origin             = "Budapest",
        destination        = "Győr",
        transport_modes    = ["intercity_bus"],
        expected_count     = 5,
    ))

    # ── Összesítő ────────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print(f"\n{'=' * 60}")
    print(f"  ÖSSZESÍTŐ: {passed}/{total} teszt sikeres")
    if passed == total:
        print("  🎉 Minden teszt sikeres!")
    else:
        print(f"  ⚠️  {total - passed} teszt sikertelen!")
    print("=" * 60)


if __name__ == "__main__":
    main()
