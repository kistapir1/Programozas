from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import get_db_connection

app = FastAPI(title="Menetrend Kereső API", version="1.0.0")

# CORS engedélyezése az Electron / Vite frontend számára (pl. localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keresési kérés struktúrája a frontend felől
class SearchRequest(BaseModel):
    origin: str
    destination: str
    waypoints: Optional[List[str]] = []
    transport_modes: Optional[List[str]] = []  # pl. ['train', 'intercity_bus']

@app.get("/")
def read_root():
    return {"message": "Menetrend Backend fut!"}

# 1. Végpont: Állomások listázása / keresése (Autocomplete-hez)
@app.get("/api/stations")
def search_stations(q: str = Query(..., min_length=1)):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT station_code, name, city, station_type FROM stations WHERE name ILIKE %s OR city ILIKE %s LIMIT 10"
        like_term = f"%{q}%"
        cur.execute(query, (like_term, like_term))
        stations = cur.fetchall()
        cur.close()
        conn.close()
        return stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Végpont: Menetrend keresés indítása a felhasználó adatai alapján
@app.post("/api/search")
def search_schedule(search: SearchRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Alap lekérdezés a stop_times, trips és routes táblák összekapcsolásával
        # Megkeressük azokat a járatokat, amelyek érintik az indulási és érkezési helyet.
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
            f"%{search.origin}%", f"%{search.origin}%",
            f"%{search.destination}%", f"%{search.destination}%"
        ]

        # Ha a felhasználó szűrt közlekedési eszközökre is a CheckboxGroup-ból
        if search.transport_modes:
            query += " AND R.transport_mode = ANY(%s)"
            params.append(search.transport_modes)

        query += " ORDER BY ST1.departure_time LIMIT 5"

        cur.execute(query, params)
        rows = cur.fetchall()

        cur.close()
        conn.close()

        # RealDictCursor már dict-et ad vissza, csak listává alakítjuk
        results = [dict(row) for row in rows]
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
