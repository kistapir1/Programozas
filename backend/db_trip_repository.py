"""
db_trip_repository.py – PostgreSQL alapú TripRepository implementáció
GTFS adatbázis (BKK Budapest) lekérdezése.
Közvetlen és átszállásos útvonalak keresése akadálymentességi és kerékpárszállítási szűrőkkel.
"""

from __future__ import annotations

import re
from typing import Optional
from database import get_db_connection
from transfer_graph import TransferGraph


def time_to_seconds(t: str) -> int:
    """Időpont (HH:MM vagy HH:MM:SS) konvertálása másodpercre."""
    if not t:
        return 0
    parts = t.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(sec: int) -> str:
    """Másodperc konvertálása HH:MM:SS formátumra."""
    hours = sec // 3600
    remainder = sec % 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def add_seconds_to_time(t: str, add_sec: int) -> str:
    """Időponthoz másodpercek hozzáadása."""
    return seconds_to_time(time_to_seconds(t) + add_sec)


def get_route_weight(short_name: str, type_name: str) -> float:
    """
    Közlekedési módok intelligens súlyozása:
    A nagy kapacitású gerincvonalak (Metró, HÉV, Villamos) előnyt élveznek az átszállópontoknál,
    míg az éjszakai buszok (9xx) nem kapnak mesterséges túlsúlyt a nappali kereséseknél.
    """
    if type_name == "Metró":
        return 15.0
    if type_name == "Elővárosi vasút / HÉV":
        return 12.0
    if type_name == "Villamos":
        return 8.0
    if short_name.startswith("9") and len(short_name) >= 3:
        return 0.2
    return 4.0


class DbTripRepository:
    """Valódi GTFS adatbázis implementáció a TripRepository protokollhoz."""

    def find_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
        departure_time_from: str | None = None,
        limit: int = 25,
        bikes_allowed: bool = False,
        wheelchair_accessible: bool = False,
        wheelchair_boarding: bool = False,
    ) -> list[dict]:
        """Közvetlen járatok keresése origin és destination között."""
        conn = get_db_connection()
        cur = conn.cursor()

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
                MIN(ST2.arrival_time::text) AS arrival_time,
                COALESCE(MAX(T.bikes_allowed), 0) AS bikes_allowed,
                COALESCE(MAX(T.wheelchair_accessible), 0) AS wheelchair_accessible,
                COALESCE(MAX(S1.wheelchair_boarding), 0) AS wheelchair_boarding
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

        if departure_time_from and departure_time_from.strip():
            formatted_time = departure_time_from.strip()
            if len(formatted_time) == 5:
                formatted_time += ":00"
            query += " AND ST1.departure_time >= %s"
            params.append(formatted_time)

        if transport_modes:
            query += " AND RT.type_name = ANY(%s)"
            params.append(transport_modes)

        # Akadálymentességi és kerékpár szűrők
        if bikes_allowed:
            query += " AND T.bikes_allowed = 1"
        if wheelchair_accessible:
            query += " AND T.wheelchair_accessible = 1"
        if wheelchair_boarding:
            query += " AND S1.wheelchair_boarding = 1 AND S2.wheelchair_boarding = 1"

        query += f"""
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
            LIMIT {limit}
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        if not rows and departure_time_from:
            fallback_params = [
                f"%{origin.strip()}%",
                f"%{destination.strip()}%",
            ]
            fallback_query = f"""
                SELECT
                    MIN(ST1.trip_id) AS trip_id,
                    R.route_short_name,
                    COALESCE(R.route_desc, R.route_long_name, '') AS route_long_name,
                    RT.type_name AS transport_mode,
                    A.agency_name AS operator,
                    S1.stop_name AS origin_station,
                    ST1.departure_time::text AS departure_time,
                    S2.stop_name AS destination_station,
                    MIN(ST2.arrival_time::text) AS arrival_time,
                    COALESCE(MAX(T.bikes_allowed), 0) AS bikes_allowed,
                    COALESCE(MAX(T.wheelchair_accessible), 0) AS wheelchair_accessible,
                    COALESCE(MAX(S1.wheelchair_boarding), 0) AS wheelchair_boarding
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

            if bikes_allowed:
                fallback_query += " AND T.bikes_allowed = 1"
            if wheelchair_accessible:
                fallback_query += " AND T.wheelchair_accessible = 1"
            if wheelchair_boarding:
                fallback_query += " AND S1.wheelchair_boarding = 1 AND S2.wheelchair_boarding = 1"

            fallback_query += f"""
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
                LIMIT {limit}
            """
            cur.execute(fallback_query, fallback_params)
            rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(row) for row in rows]

    def find_transfer_hubs(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str] | None = None,
        limit: int = 15,
        bikes_allowed: bool = False,
        wheelchair_accessible: bool = False,
        wheelchair_boarding: bool = False,
    ) -> list[dict]:
        """
        Megkeresi azokat a közbenső átszállási csomópontokat,
        amelyek valódi kapcsolatot biztosítanak origin és destination között.
        Figyelembe veszi az akadálymentességet és a kerékpárszállítást is.
        """
        tg = TransferGraph.instance()
        conn = get_db_connection()
        cur = conn.cursor()

        # Vonalak súlyozásának betöltése
        cur.execute(
            """
            SELECT r.route_id, r.route_short_name, rt.type_name
            FROM routes r
            JOIN route_types rt ON r.route_type = rt.route_type
            """
        )
        route_weights = {
            r["route_id"]: get_route_weight(r["route_short_name"], r["type_name"])
            for r in cur.fetchall()
        }

        # 1. Megállók azonosítása
        origin_stops_query = """
            SELECT stop_id, stop_name, wheelchair_boarding FROM stops
            WHERE stop_name ILIKE %s AND (location_type = 0 OR location_type IS NULL)
        """
        if wheelchair_boarding:
            origin_stops_query += " AND wheelchair_boarding = 1"

        cur.execute(origin_stops_query, (f"%{origin.strip()}%",))
        origin_stops_raw = cur.fetchall()
        origin_stops = {r["stop_id"]: r["stop_name"] for r in origin_stops_raw}

        dest_stops_query = """
            SELECT stop_id, stop_name, wheelchair_boarding FROM stops
            WHERE stop_name ILIKE %s AND (location_type = 0 OR location_type IS NULL)
        """
        if wheelchair_boarding:
            dest_stops_query += " AND wheelchair_boarding = 1"

        cur.execute(dest_stops_query, (f"%{destination.strip()}%",))
        dest_stops_raw = cur.fetchall()
        dest_stops = {r["stop_id"]: r["stop_name"] for r in dest_stops_raw}

        if not origin_stops or not dest_stops:
            cur.close()
            conn.close()
            return []

        # 2. Vonalak, amelyek érintik az origint és a destet
        routes_filter_extra = ""
        if bikes_allowed:
            routes_filter_extra += " AND t.bikes_allowed = 1"
        if wheelchair_accessible:
            routes_filter_extra += " AND t.wheelchair_accessible = 1"

        cur.execute(
            f"""
            SELECT DISTINCT t.route_id
            FROM trips t
            JOIN stop_times st ON t.trip_id = st.trip_id
            WHERE st.stop_id = ANY(%s) {routes_filter_extra}
            """,
            (list(origin_stops.keys()),),
        )
        origin_routes = [r["route_id"] for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT DISTINCT t.route_id
            FROM trips t
            JOIN stop_times st ON t.trip_id = st.trip_id
            WHERE st.stop_id = ANY(%s) {routes_filter_extra}
            """,
            (list(dest_stops.keys()),),
        )
        dest_routes = [r["route_id"] for r in cur.fetchall()]

        if not origin_routes or not dest_routes:
            cur.close()
            conn.close()
            return []

        # 3. Origin és dest vonalak megállói
        stop_boarding_filter = " AND s.wheelchair_boarding = 1" if wheelchair_boarding else ""

        cur.execute(
            f"""
            SELECT DISTINCT t.route_id, st.stop_id, s.stop_name, s.wheelchair_boarding
            FROM trips t
            JOIN stop_times st ON t.trip_id = st.trip_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE t.route_id = ANY(%s) {stop_boarding_filter}
            """,
            (origin_routes,),
        )
        origin_route_stops = cur.fetchall()

        cur.execute(
            f"""
            SELECT DISTINCT t.route_id, st.stop_id, s.stop_name, s.wheelchair_boarding
            FROM trips t
            JOIN stop_times st ON t.trip_id = st.trip_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE t.route_id = ANY(%s) {stop_boarding_filter}
            """,
            (dest_routes,),
        )
        dest_route_stops = cur.fetchall()

        cur.close()
        conn.close()

        dest_stop_map = {}
        dest_stop_routes = {}
        for r in dest_route_stops:
            sid = r["stop_id"]
            dest_stop_map[sid] = r["stop_name"]
            dest_stop_routes.setdefault(sid, set()).add(r["route_id"])

        origin_stop_routes = {}
        origin_stop_map = {}
        for r in origin_route_stops:
            sid = r["stop_id"]
            origin_stop_map[sid] = r["stop_name"]
            origin_stop_routes.setdefault(sid, set()).add(r["route_id"])

        hub_candidates: dict[tuple[str, str], dict] = {}

        # a) Közvetlen egyezés (ugyanaz a megálló / 60s átszállási ráhagyás)
        common_sids = set(origin_stop_routes.keys()) & set(dest_stop_routes.keys())
        for sid in common_sids:
            if sid in origin_stops or sid in dest_stops:
                continue
            sname = origin_stop_map[sid]
            score = sum(route_weights.get(r, 1.0) for r in origin_stop_routes[sid]) * sum(
                route_weights.get(r, 1.0) for r in dest_stop_routes[sid]
            )
            key = (sname, sname)
            if key not in hub_candidates or score > hub_candidates[key]["score"]:
                hub_candidates[key] = {
                    "from_stop_name": sname,
                    "to_stop_name": sname,
                    "walk_seconds": 60,
                    "score": score,
                }

        # b) TransferGraph élek (parent_station, pathways, hasonló név)
        for s_orig, r_orig_set in origin_stop_routes.items():
            if s_orig in origin_stops:
                continue
            for s_dest, walk_sec in tg.get_transfers(s_orig):
                if s_dest in dest_stop_routes and s_dest not in dest_stops:
                    from_name = origin_stop_map[s_orig]
                    to_name = dest_stop_map[s_dest]
                    score = sum(route_weights.get(r, 1.0) for r in r_orig_set) * sum(
                        route_weights.get(r, 1.0) for r in dest_stop_routes[s_dest]
                    )
                    key = (from_name, to_name)
                    if key not in hub_candidates or score > hub_candidates[key]["score"]:
                        hub_candidates[key] = {
                            "from_stop_name": from_name,
                            "to_stop_name": to_name,
                            "walk_seconds": walk_sec,
                            "score": score,
                        }

        sorted_hubs = sorted(hub_candidates.values(), key=lambda h: h["score"], reverse=True)
        return sorted_hubs[:limit]

    def find_transfer_trips(
        self,
        origin: str,
        destination: str,
        transport_modes: list[str],
        departure_time_from: str | None = None,
        max_transfers: int = 1,
        min_transfer_seconds: int = 300,
        bikes_allowed: bool = False,
        wheelchair_accessible: bool = False,
        wheelchair_boarding: bool = False,
    ) -> list[dict]:
        """
        Átszállásos útvonalak keresése.
        Figyelembe veszi a minimális átszállási időt, kerékpárszállítást és akadálymentességet.
        """
        if max_transfers < 1:
            return []

        hubs = self.find_transfer_hubs(
            origin,
            destination,
            transport_modes,
            limit=12,
            bikes_allowed=bikes_allowed,
            wheelchair_accessible=wheelchair_accessible,
            wheelchair_boarding=wheelchair_boarding,
        )

        found_journeys: list[dict] = []
        seen_combos: set[tuple[str, str, str, str]] = set()

        ref_sec = time_to_seconds(departure_time_from) if departure_time_from else 0

        for hub in hubs:
            hub_from = hub["from_stop_name"]
            hub_to = hub["to_stop_name"]
            effective_transfer_sec = max(hub["walk_seconds"], min_transfer_seconds)

            # 1. Szakasz (Leg 1): Origin -> Hub From
            leg1_candidates = self.find_trips(
                origin,
                hub_from,
                transport_modes,
                departure_time_from,
                limit=3,
                bikes_allowed=bikes_allowed,
                wheelchair_accessible=wheelchair_accessible,
                wheelchair_boarding=wheelchair_boarding,
            )

            for leg1 in leg1_candidates:
                if departure_time_from:
                    l1_dep_sec = time_to_seconds(leg1["departure_time"])
                    if l1_dep_sec < ref_sec:
                        l1_dep_sec += 24 * 3600
                    if (l1_dep_sec - ref_sec) > 4 * 3600:
                        continue

                # 2. Szakasz (Leg 2): Hub To -> Destination
                leg2_min_dep = add_seconds_to_time(leg1["arrival_time"], effective_transfer_sec)

                leg2_candidates = self.find_trips(
                    hub_to,
                    destination,
                    transport_modes,
                    leg2_min_dep,
                    limit=2,
                    bikes_allowed=bikes_allowed,
                    wheelchair_accessible=wheelchair_accessible,
                    wheelchair_boarding=wheelchair_boarding,
                )

                for leg2 in leg2_candidates:
                    if leg1.get("trip_id") == leg2.get("trip_id"):
                        continue

                    combo_key = (
                        leg1["route_short_name"],
                        leg1["departure_time"],
                        leg2["route_short_name"],
                        leg2["departure_time"],
                    )
                    if combo_key in seen_combos:
                        continue
                    seen_combos.add(combo_key)

                    journey_bikes = 1 if (leg1.get("bikes_allowed") == 1 and leg2.get("bikes_allowed") == 1) else 0
                    journey_wheelchair = 1 if (leg1.get("wheelchair_accessible") == 1 and leg2.get("wheelchair_accessible") == 1) else 0

                    journey = {
                        "trip_id": leg1["trip_id"],
                        "route_short_name": f"{leg1['route_short_name']} → {leg2['route_short_name']}",
                        "route_long_name": f"{leg1['route_long_name']} / {leg2['route_long_name']}",
                        "transport_mode": leg1["transport_mode"],
                        "operator": leg1["operator"] if leg1["operator"] == leg2["operator"] else f"{leg1['operator']}, {leg2['operator']}",
                        "origin_station": leg1["origin_station"],
                        "departure_time": leg1["departure_time"],
                        "destination_station": leg2["destination_station"],
                        "arrival_time": leg2["arrival_time"],
                        "transfers": 1,
                        "bikes_allowed": journey_bikes,
                        "wheelchair_accessible": journey_wheelchair,
                        "legs": [
                            {
                                "route_short_name": leg1["route_short_name"],
                                "route_long_name": leg1["route_long_name"],
                                "transport_mode": leg1["transport_mode"],
                                "operator": leg1["operator"],
                                "origin_station": leg1["origin_station"],
                                "departure_time": leg1["departure_time"],
                                "destination_station": leg1["destination_station"],
                                "arrival_time": leg1["arrival_time"],
                                "bikes_allowed": leg1.get("bikes_allowed", 0),
                                "wheelchair_accessible": leg1.get("wheelchair_accessible", 0),
                            },
                            {
                                "route_short_name": leg2["route_short_name"],
                                "route_long_name": leg2["route_long_name"],
                                "transport_mode": leg2["transport_mode"],
                                "operator": leg2["operator"],
                                "origin_station": leg2["origin_station"],
                                "departure_time": leg2["departure_time"],
                                "destination_station": leg2["destination_station"],
                                "arrival_time": leg2["arrival_time"],
                                "walk_seconds_before": effective_transfer_sec,
                                "transfer_station": leg1["destination_station"],
                                "bikes_allowed": leg2.get("bikes_allowed", 0),
                                "wheelchair_accessible": leg2.get("wheelchair_accessible", 0),
                            },
                        ],
                    }
                    found_journeys.append(journey)

        # Ha 2 átszállás engedélyezett és kevés a találat:
        if max_transfers >= 2 and len(found_journeys) < 3 and len(hubs) >= 2:
            for i in range(min(2, len(hubs))):
                for j in range(i + 1, min(4, len(hubs))):
                    h1 = hubs[i]["from_stop_name"]
                    h2 = hubs[j]["to_stop_name"]
                    leg1_candidates = self.find_trips(
                        origin,
                        h1,
                        transport_modes,
                        departure_time_from,
                        limit=2,
                        bikes_allowed=bikes_allowed,
                        wheelchair_accessible=wheelchair_accessible,
                        wheelchair_boarding=wheelchair_boarding,
                    )
                    for leg1 in leg1_candidates:
                        mid_dep = add_seconds_to_time(leg1["arrival_time"], max(120, min_transfer_seconds))
                        mid_trips = self.find_trips(
                            h1,
                            h2,
                            transport_modes,
                            mid_dep,
                            limit=2,
                            bikes_allowed=bikes_allowed,
                            wheelchair_accessible=wheelchair_accessible,
                            wheelchair_boarding=wheelchair_boarding,
                        )
                        for mid in mid_trips:
                            leg3_dep = add_seconds_to_time(mid["arrival_time"], max(120, min_transfer_seconds))
                            leg3_candidates = self.find_trips(
                                h2,
                                destination,
                                transport_modes,
                                leg3_dep,
                                limit=1,
                                bikes_allowed=bikes_allowed,
                                wheelchair_accessible=wheelchair_accessible,
                                wheelchair_boarding=wheelchair_boarding,
                            )
                            for leg3 in leg3_candidates:
                                journey = {
                                    "trip_id": leg1["trip_id"],
                                    "route_short_name": f"{leg1['route_short_name']} → {mid['route_short_name']} → {leg3['route_short_name']}",
                                    "route_long_name": f"{leg1['route_long_name']} / {mid['route_long_name']} / {leg3['route_long_name']}",
                                    "transport_mode": leg1["transport_mode"],
                                    "operator": leg1["operator"],
                                    "origin_station": leg1["origin_station"],
                                    "departure_time": leg1["departure_time"],
                                    "destination_station": leg3["destination_station"],
                                    "arrival_time": leg3["arrival_time"],
                                    "transfers": 2,
                                    "bikes_allowed": 1 if (leg1.get("bikes_allowed") == 1 and mid.get("bikes_allowed") == 1 and leg3.get("bikes_allowed") == 1) else 0,
                                    "wheelchair_accessible": 1 if (leg1.get("wheelchair_accessible") == 1 and mid.get("wheelchair_accessible") == 1 and leg3.get("wheelchair_accessible") == 1) else 0,
                                    "legs": [
                                        {
                                            "route_short_name": leg1["route_short_name"],
                                            "route_long_name": leg1["route_long_name"],
                                            "transport_mode": leg1["transport_mode"],
                                            "operator": leg1["operator"],
                                            "origin_station": leg1["origin_station"],
                                            "departure_time": leg1["departure_time"],
                                            "destination_station": leg1["destination_station"],
                                            "arrival_time": leg1["arrival_time"],
                                            "bikes_allowed": leg1.get("bikes_allowed", 0),
                                            "wheelchair_accessible": leg1.get("wheelchair_accessible", 0),
                                        },
                                        {
                                            "route_short_name": mid["route_short_name"],
                                            "route_long_name": mid["route_long_name"],
                                            "transport_mode": mid["transport_mode"],
                                            "operator": mid["operator"],
                                            "origin_station": mid["origin_station"],
                                            "departure_time": mid["departure_time"],
                                            "destination_station": mid["destination_station"],
                                            "arrival_time": mid["arrival_time"],
                                            "walk_seconds_before": max(120, min_transfer_seconds),
                                            "transfer_station": leg1["destination_station"],
                                            "bikes_allowed": mid.get("bikes_allowed", 0),
                                            "wheelchair_accessible": mid.get("wheelchair_accessible", 0),
                                        },
                                        {
                                            "route_short_name": leg3["route_short_name"],
                                            "route_long_name": leg3["route_long_name"],
                                            "transport_mode": leg3["transport_mode"],
                                            "operator": leg3["operator"],
                                            "origin_station": leg3["origin_station"],
                                            "departure_time": leg3["departure_time"],
                                            "destination_station": leg3["destination_station"],
                                            "arrival_time": leg3["arrival_time"],
                                            "walk_seconds_before": max(120, min_transfer_seconds),
                                            "transfer_station": mid["destination_station"],
                                            "bikes_allowed": leg3.get("bikes_allowed", 0),
                                            "wheelchair_accessible": leg3.get("wheelchair_accessible", 0),
                                        },
                                    ],
                                }
                                found_journeys.append(journey)

        return found_journeys
