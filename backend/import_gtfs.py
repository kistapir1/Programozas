"""
import_gtfs.py – GTFS adatok villámgyors beimportálása PostgreSQL-be
"""

import os
import sys
import time
import zipfile
import io
import csv
import psycopg2
from database import get_db_connection

def run_import():
    gtfs_dir = os.environ.get("GTFS_DIR", "/GTFS")
    if not os.path.exists(gtfs_dir):
        # Ha lokálisan futna:
        gtfs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "GTFS"))
    
    print(f"[*] GTFS könyvtár: {gtfs_dir}")
    if not os.path.exists(gtfs_dir):
        print(f"[!] Nem található a GTFS könyvtár: {gtfs_dir}")
        sys.exit(1)

    schema_file = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    if not os.path.exists(schema_file):
        schema_file = "/docker-entrypoint-initdb.d/schema.sql"
    if not os.path.exists(schema_file):
        schema_file = "schema.sql"

    print("[*] Kapcsolódás az adatbázishoz...")
    conn = get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()

    # 1. Séma futtatása
    print(f"[*] Séma inicializálása ({schema_file})...")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    cur.execute(schema_sql)
    conn.commit()
    print("[+] Séma és lookup táblák sikeresen létrehozva.")

    # Kikapcsoljuk az indexeket/triggereket a gyors másoláshoz
    cur.execute("SET session_replication_role = 'replica';")

    # 2. Agency import
    agency_path = os.path.join(gtfs_dir, "agency.txt")
    if os.path.exists(agency_path):
        print("[*] agency.txt importálása...")
        with open(agency_path, "r", encoding="utf-8-sig") as f:
            cur.copy_expert("COPY agency (agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        print("[+] Agency kész.")

    # 3. Routes import
    routes_path = os.path.join(gtfs_dir, "routes.txt")
    if os.path.exists(routes_path):
        print("[*] routes.txt importálása...")
        with open(routes_path, "r", encoding="utf-8-sig") as f:
            cur.copy_expert("COPY routes (agency_id, route_id, route_short_name, route_long_name, route_type, route_desc, route_color, route_text_color, route_sort_order) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        print("[+] Routes kész.")

    # 4. Stops import (CSV-ben location_sub_type van, a táblában location_subtype)
    stops_path = os.path.join(gtfs_dir, "stops.txt")
    if os.path.exists(stops_path):
        print("[*] stops.txt importálása...")
        # Beolvassuk és a fejlécet igazítjuk, ha kell
        with open(stops_path, "r", encoding="utf-8-sig") as f:
            header_line = f.readline().strip()
            # Cseréljük a location_sub_type-ot location_subtype-ra
            header_line = header_line.replace("location_sub_type", "location_subtype")
            
            # Memória stream az átírt fejléccel
            buf = io.StringIO()
            buf.write(header_line + "\n")
            buf.write(f.read())
            buf.seek(0)
            
            cur.copy_expert("COPY stops (stop_id, stop_name, stop_lat, stop_lon, stop_code, location_type, location_subtype, parent_station, wheelchair_boarding) FROM STDIN WITH (FORMAT csv, HEADER true)", buf)
        conn.commit()
        print("[+] Stops kész.")

    # 5. Trips import
    trips_path = os.path.join(gtfs_dir, "trips.txt")
    if os.path.exists(trips_path):
        print("[*] trips.txt importálása...")
        with open(trips_path, "r", encoding="utf-8-sig") as f:
            cur.copy_expert("COPY trips (route_id, trip_id, service_id, trip_headsign, direction_id, block_id, shape_id, wheelchair_accessible, bikes_allowed) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        print("[+] Trips kész.")

    # 6. Stop times import (zip fájlból kicsomagolva / streamelve)
    stop_times_zip = os.path.join(gtfs_dir, "stop_times.zip")
    stop_times_txt = os.path.join(gtfs_dir, "stop_times.txt")
    
    if os.path.exists(stop_times_txt):
        print("[*] stop_times.txt importálása (közvetlen fájlból)...")
        with open(stop_times_txt, "r", encoding="utf-8-sig") as f:
            cur.copy_expert("COPY stop_times (trip_id, stop_id, arrival_time, departure_time, stop_sequence, stop_headsign, pickup_type, drop_off_type, shape_dist_traveled) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        print("[+] Stop times kész.")
    elif os.path.exists(stop_times_zip):
        print("[*] stop_times.zip kicsomagolása és importálása streamelve...")
        start_t = time.time()
        with zipfile.ZipFile(stop_times_zip, 'r') as z:
            with z.open('stop_times.txt') as zf:
                # TextIOWrapper-rel olvassuk a bináris zip streamet
                with io.TextIOWrapper(zf, encoding='utf-8') as text_stream:
                    cur.copy_expert("COPY stop_times (trip_id, stop_id, arrival_time, departure_time, stop_sequence, stop_headsign, pickup_type, drop_off_type, shape_dist_traveled) FROM STDIN WITH (FORMAT csv, HEADER true)", text_stream)
        conn.commit()
        print(f"[+] Stop times kész ({round(time.time() - start_t, 1)} mp alatt).")

    # Visszaállítjuk a triggereket és indexeket
    cur.execute("SET session_replication_role = 'origin';")
    conn.commit()

    # Statisztikák kiírása
    print("\n[=== ADATBÁZIS STATISZTIKÁK ===]")
    for table in ["agency", "routes", "stops", "trips", "stop_times", "route_types"]:
        cur.execute(f"SELECT count(*) FROM {table}")
        count = cur.fetchone()['count']
        print(f"  - {table}: {count:,} sor")

    cur.close()
    conn.close()
    print("[+] Minden GTFS adat sikeresen betöltve az adatbázisba!")

if __name__ == "__main__":
    run_import()
