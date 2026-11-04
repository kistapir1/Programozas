"""
db_trip_repository.py – PostgreSQL alapú TripRepository implementáció
Ezt használja a valódi FastAPI végpont (a stub-ot az integrációs teszt).
"""

from database import get_db_connection


class DbTripRepository:
    """Valódi adatbázis implementáció a TripRepository protokollhoz."""

    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
    ) -> list[dict]:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
                ST1.trip_id,
                R.route_short_name,
                R.route_long_name,
                R.transport_mode,
                R.operator,
                S1.name AS origin_station,
                ST1.departure_time::text AS departure_time,
                S2.name AS destination_station,
                ST2.arrival_time::text AS arrival_time
            FROM stop_times ST1
            JOIN stop_times ST2 ON ST1.trip_id = ST2.trip_id
            JOIN trips T ON ST1.trip_id = T.trip_id
            JOIN routes R ON T.route_id = R.route_id
            JOIN stations S1 ON ST1.station_id = S1.station_id
            JOIN stations S2 ON ST2.station_id = S2.station_id
            WHERE (S1.name ILIKE %s OR S1.city ILIKE %s)
              AND (S2.name ILIKE %s OR S2.city ILIKE %s)
              AND ST1.stop_sequence < ST2.stop_sequence
        """

        params: list = [
            f"%{origin}%", f"%{origin}%",
            f"%{destination}%", f"%{destination}%",
        ]

        if transport_modes:
            query += " AND R.transport_mode = ANY(%s)"
            params.append(transport_modes)

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [dict(row) for row in rows]
