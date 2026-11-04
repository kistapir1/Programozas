from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from db_trip_repository import DbTripRepository
from schedule_search_service import ScheduleSearchService

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

# 1. Végpont: Állomások listázása / keresése (Autocomplete-hez)
@app.get("/api/stations")
def search_stations(q: str = Query(..., min_length=1)):
    try:
        from database import get_db_connection
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

# 2. Végpont: Menetrend keresés – a ScheduleSearchService-t használja
@app.post("/api/search")
def search_schedule(search: SearchRequest):
    try:
        repo = DbTripRepository()
        service = ScheduleSearchService(repo)
        result = service.search(
            origin=search.origin,
            destination=search.destination,
            transport_modes=list(search.transport_modes or []),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
