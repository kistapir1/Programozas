from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import get_db_connection
from db_trip_repository import DbTripRepository
from schedule_search_service import ScheduleSearchService
from auth import router as auth_router

app = FastAPI(title="Menetrend Kereső API", version="1.0.0")

# CORS engedélyezése az Electron / Vite frontend számára
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regisztráció / belépés végpontok (/api/auth/...)
app.include_router(auth_router)

# Keresési kérés struktúrája a frontend felől
class SearchRequest(BaseModel):
    origin: str
    destination: str
    waypoints: Optional[List[str]] = []
    transport_modes: Optional[List[str]] = []
    max_transfers: Optional[int] = 2
    time_mode: Optional[str] = "departure"
    date: Optional[str] = None
    time: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Menetrend Backend fut (BKK GTFS adatbázis aktív)!"}


# 1. Végpont: Állomások listázása / autocomplete (ékezet-független unaccent kereséssel)
@app.get("/api/stations")
def search_stations(q: str = Query(..., min_length=1)):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # unaccent-tel keresünk, hogy ékezet nélkül gépelve is megtalálja (pl. 'deak' -> 'Deák Ferenc tér')
        query = """
            SELECT DISTINCT stop_name AS name
            FROM stops
            WHERE unaccent(stop_name) ILIKE unaccent(%s)
            ORDER BY stop_name
            LIMIT 10
        """
        like_term = f"%{q.strip()}%"
        cur.execute(query, (like_term,))
        stations = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(s) for s in stations]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# 2. Végpont: Menetrend keresés
@app.post("/api/search")
def search_schedule(search: SearchRequest):
    try:
        print(f"\n[API KÉRÉS] origin='{search.origin}', dest='{search.destination}', time='{search.time}', time_mode='{search.time_mode}', modes={search.transport_modes}")
        repo = DbTripRepository()
        service = ScheduleSearchService(repo)
        
        # Ha departure módban van és van megadva időpont, figyelembe vesszük
        time_filter = search.time if search.time_mode == "departure" and search.time else None
        
        result = service.search(
            origin=search.origin,
            destination=search.destination,
            transport_modes=list(search.transport_modes or []),
            departure_time_from=time_filter,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
