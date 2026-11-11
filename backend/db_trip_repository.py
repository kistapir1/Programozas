"""
db_trip_repository.py – PostgreSQL alapú TripRepository implementáció
GTFS adatbázis (BKK Budapest) lekérdezése.
A járműtípus szűrés közvetlenül a route_types.type_name mezőre illeszkedik,
nincs mesterséges kód-leképezés.
"""

from database import get_db_connection


class DbTripRepository:
    """Valódi GTFS adatbázis implementáció a TripRepository protokollhoz."""

    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
        departure_time_from: str | None = None,
    ) -> list[dict]:
        conn = get_db_connection()
        cur = conn.cursor()

        print(f"[*] Keresés: origin='{origin}', dest='{destination}', modes={transport_modes}, time_from='{departure_time_from}'")

        query = """
            SELECT
                MIN(ST1.trip_id) AS trip_id,
                R.route_short_name,
                COALESCE(R.route_desc, R.route_long_name, '') AS route_long_name,
                RT.type_name AS transport_mode,
                A.agency_name AS operator,
                S1.stop_name AS origin_station,
                ST1.departure_time::text AS departure_time,
                S2.stop_name AS destination_station,
                MIN(ST2.arrival_time::text) AS arrival_time
            FROM stops S1
            JOIN stop_times ST1 ON S1.stop_id = ST1.stop_id
            JOIN stop_times ST2 ON ST1.trip_id = ST2.trip_id
            JOIN stops S2 ON ST2.stop_id = S2.stop_id
            JOIN trips T ON ST1.trip_id = T.trip_id
            JOIN routes R ON T.route_id = R.route_id
            JOIN route_types RT ON R.route_type = RT.route_type
            JOIN agency A ON R.agency_id = A.agency_id
            WHERE (S1.stop_name ILIKE %s)
              AND (S2.stop_name ILIKE %s)
              AND ST1.stop_sequence < ST2.stop_sequence
        """

        params: list = [
            f"%{origin.strip()}%",
            f"%{destination.strip()}%",
        ]

        # Időpont szűrés (pl. "09:15" -> "09:15:00")
        if departure_time_from and departure_time_from.strip():
            formatted_time = departure_time_from.strip()
            if len(formatted_time) == 5:
                formatted_time += ":00"
            query += " AND ST1.departure_time >= %s"
            params.append(formatted_time)

        # Járműtípus szűrés: közvetlenül a frontend által küldött adatbázisbeli type_name értékekre
        if transport_modes:
            query += " AND RT.type_name = ANY(%s)"
            params.append(transport_modes)
            print(f"[*] Szűrt járműtípusok az SQL-ben (type_name): {transport_modes}")

        # Csoportosítás és INDULÁSI IDŐ SZERINTI RENDEZÉS
        query += """
            GROUP BY 
                R.route_short_name, 
                R.route_desc, 
                R.route_long_name, 
                RT.type_name, 
                A.agency_name, 
                S1.stop_name, 
                ST1.departure_time, 
                S2.stop_name
            ORDER BY ST1.departure_time ASC
            LIMIT 25
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        # Ha a nap végén kerestünk és nincs találat az adott időpont után,
        # lekérjük a legkorábbi másnapi járatokat
        if not rows and departure_time_from:
            print("[*] Nincs több járat a megadott időpont után aznap, korábbi járatok keresése...")
            fallback_params = [
                f"%{origin.strip()}%",
                f"%{destination.strip()}%",
            ]
            fallback_query = """
                SELECT
                    MIN(ST1.trip_id) AS trip_id,
                    R.route_short_name,
                    COALESCE(R.route_desc, R.route_long_name, '') AS route_long_name,
                    RT.type_name AS transport_mode,
                    A.agency_name AS operator,
                    S1.stop_name AS origin_station,
                    ST1.departure_time::text AS departure_time,
                    S2.stop_name AS destination_station,
                    MIN(ST2.arrival_time::text) AS arrival_time
                FROM stops S1
                JOIN stop_times ST1 ON S1.stop_id = ST1.stop_id
                JOIN stop_times ST2 ON ST1.trip_id = ST2.trip_id
                JOIN stops S2 ON ST2.stop_id = S2.stop_id
                JOIN trips T ON ST1.trip_id = T.trip_id
                JOIN routes R ON T.route_id = R.route_id
                JOIN route_types RT ON R.route_type = RT.route_type
                JOIN agency A ON R.agency_id = A.agency_id
                WHERE (S1.stop_name ILIKE %s)
                  AND (S2.stop_name ILIKE %s)
                  AND ST1.stop_sequence < ST2.stop_sequence
            """
            if transport_modes:
                fallback_query += " AND RT.type_name = ANY(%s)"
                fallback_params.append(transport_modes)

            fallback_query += """
                GROUP BY 
                    R.route_short_name, 
                    R.route_desc, 
                    R.route_long_name, 
                    RT.type_name, 
                    A.agency_name, 
                    S1.stop_name, 
                    ST1.departure_time, 
                    S2.stop_name
                ORDER BY ST1.departure_time ASC
                LIMIT 25
            """
            cur.execute(fallback_query, fallback_params)
            rows = cur.fetchall()

        cur.close()
        conn.close()

        print(f"[+] SQL találatok száma: {len(rows)}")
        results = [dict(row) for row in rows]
        return results
