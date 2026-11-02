-- 1. ADATBÁZIS ÉS SÉMA LÉTREHOZÁSA (PostgreSQL)

DROP TABLE IF EXISTS calendar CASCADE;
DROP TABLE IF EXISTS stop_times CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS stations CASCADE;

CREATE TABLE stations (
    station_id SERIAL PRIMARY KEY,
    station_code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    station_type VARCHAR(20) NOT NULL CHECK (station_type IN ('train_station', 'bus_station', 'local_bus_stop')),
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6)
);

CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    route_short_name VARCHAR(20) NOT NULL, -- pl. 'S10', 'IC 934', '7020', '1Y'
    route_long_name VARCHAR(150),          -- pl. 'Győr - Sopron - Szombathely'
    transport_mode VARCHAR(20) NOT NULL CHECK (transport_mode IN ('train', 'intercity_bus', 'local_bus')),
    operator VARCHAR(50) NOT NULL           -- pl. 'MÁV-START', 'Volánbusz', 'Győr Helyi Közlekedés'
);

CREATE TABLE trips (
    trip_id SERIAL PRIMARY KEY,
    route_id INT REFERENCES routes(route_id) ON DELETE CASCADE,
    trip_number VARCHAR(30),
    direction VARCHAR(50),
    headsign VARCHAR(100)
);

CREATE TABLE stop_times (
    stop_time_id SERIAL PRIMARY KEY,
    trip_id INT REFERENCES trips(trip_id) ON DELETE CASCADE,
    station_id INT REFERENCES stations(station_id) ON DELETE RESTRICT,
    arrival_time TIME,
    departure_time TIME,
    stop_sequence INT NOT NULL
);

CREATE TABLE calendar (
    calendar_id SERIAL PRIMARY KEY,
    trip_id INT REFERENCES trips(trip_id) ON DELETE CASCADE,
    runs_on_mondays BOOLEAN DEFAULT TRUE,
    runs_on_tuesdays BOOLEAN DEFAULT TRUE,
    runs_on_wednesdays BOOLEAN DEFAULT TRUE,
    runs_on_thursdays BOOLEAN DEFAULT TRUE,
    runs_on_fridays BOOLEAN DEFAULT TRUE,
    runs_on_saturdays BOOLEAN DEFAULT TRUE,
    runs_on_sundays BOOLEAN DEFAULT TRUE,
    valid_from DATE DEFAULT '2026-01-01',
    valid_to DATE DEFAULT '2026-12-31'
);

-- Indexek a gyorsabb lekérdezésekhez
CREATE INDEX idx_stations_city ON stations(city);
CREATE INDEX idx_stations_type ON stations(station_type);
CREATE INDEX idx_routes_mode ON routes(transport_mode);
CREATE INDEX idx_stop_times_trip ON stop_times(trip_id);
CREATE INDEX idx_stop_times_station ON stop_times(station_id);

-- 2. PÉLDA ADATOK FELTÖLTÉSE

-- Állomások és Megállók
INSERT INTO stations (station_code, name, city, station_type) VALUES 
-- Vonatállomások
('GYOR_RAIL', 'Győr vasútállomás', 'Győr', 'train_station'),
('BUDAPEST_KELETI', 'Budapest-Keleti', 'Budapest', 'train_station'),
('BUDAPEST_KELENFOLD', 'Budapest-Kelenföld', 'Budapest', 'train_station'),
('SOPRON_RAIL', 'Sopron vasútállomás', 'Sopron', 'train_station'),
('SZOMBATHELY_RAIL', 'Szombathely vasútállomás', 'Szombathely', 'train_station'),
('VESZPREM_RAIL', 'Veszprém vasútállomás', 'Veszprém', 'train_station'),
('CSORNA_RAIL', 'Csorna vasútállomás', 'Csorna', 'train_station'),

-- Helyközi buszállomások
('GYOR_BUSZ', 'Győr autóbusz-állomás', 'Győr', 'bus_station'),
('BUDAPEST_NEPLIGET', 'Budapest Népliget autóbusz-pályaudvar', 'Budapest', 'bus_station'),
('VESZPREM_BUSZ', 'Veszprém autóbusz-állomás', 'Veszprém', 'bus_station'),

-- Győri helyi buszmegállók
('GYOR_AUDI_1', 'Győr, Audi gyár 8-as porta', 'Győr', 'local_bus_stop'),
('GYOR_MARCAL_VAROS', 'Győr, Marcalváros', 'Győr', 'local_bus_stop'),
('GYOR_SZZE', 'Győr, Széchenyi István Egyetem', 'Győr', 'local_bus_stop'),
('GYOR_VAROSHÁZA', 'Győr, Városháza', 'Győr', 'local_bus_stop');

-- Járatok / Vonali törzsadatok
INSERT INTO routes (route_short_name, route_long_name, transport_mode, operator) VALUES 
('IC 934', 'Budapest - Győr - Sopron (InterCity)', 'train', 'MÁV-START'),
('S10', 'Budapest - Tatabánya - Győr (Személyvonat)', 'train', 'MÁV-START'),
('7020', 'Győr - Veszprém helyközi autóbusz', 'intercity_bus', 'Volánbusz'),
('1', 'Marcalváros - Győr-Újváros (Győr Helyi)', 'local_bus', 'Volánbusz Győr'),
('1Y', 'Marcalváros - Audi gyár (Győr Helyi)', 'local_bus', 'Volánbusz Győr');

-- Út / Utazás példák (Trips)
INSERT INTO trips (route_id, trip_number, direction, headsign) VALUES 
(1, 'IC934_1', 'Oda', 'Sopron'),
(3, 'VOLAN_7020_1', 'Oda', 'Veszprém'),
(5, 'LOC_1Y_1', 'Oda', 'Audi gyár');

-- Megállási idők (Stop Times)
-- 1. IC 934 (Győr -> Sopron)
INSERT INTO stop_times (trip_id, station_id, arrival_time, departure_time, stop_sequence) VALUES 
(1, (SELECT station_id FROM stations WHERE station_code = 'GYOR_RAIL'), NULL, '08:21:00', 1),
(1, (SELECT station_id FROM stations WHERE station_code = 'CSORNA_RAIL'), '08:42:00', '08:44:00', 2),
(1, (SELECT station_id FROM stations WHERE station_code = 'SOPRON_RAIL'), '09:25:00', NULL, 3);

-- 2. Helyközi busz (Győr -> Veszprém)
INSERT INTO stop_times (trip_id, station_id, arrival_time, departure_time, stop_sequence) VALUES 
(2, (SELECT station_id FROM stations WHERE station_code = 'GYOR_BUSZ'), NULL, '10:00:00', 1),
(2, (SELECT station_id FROM stations WHERE station_code = 'VESZPREM_BUSZ'), '11:25:00', NULL, 2);

-- 3. Győri helyi járat 1Y (Marcalváros -> Városháza -> Audi gyár)
INSERT INTO stop_times (trip_id, station_id, arrival_time, departure_time, stop_sequence) VALUES 
(3, (SELECT station_id FROM stations WHERE station_code = 'GYOR_MARCAL_VAROS'), NULL, '07:05:00', 1),
(3, (SELECT station_id FROM stations WHERE station_code = 'GYOR_VAROSHÁZA'), '07:15:00', '07:16:00', 2),
(3, (SELECT station_id FROM stations WHERE station_code = 'GYOR_AUDI_1'), '07:32:00', NULL, 3);

-- Naptár (Közlekedési napok)
INSERT INTO calendar (trip_id, runs_on_mondays, runs_on_tuesdays, runs_on_wednesdays, runs_on_thursdays, runs_on_fridays) VALUES 
(1, TRUE, TRUE, TRUE, TRUE, TRUE),
(2, TRUE, TRUE, TRUE, TRUE, TRUE),
(3, TRUE, TRUE, TRUE, TRUE, TRUE);


