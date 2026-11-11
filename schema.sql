-- 1. ADATBÁZIS ÉS SÉMA LÉTREHOZÁSA (PostgreSQL)

DROP TABLE IF EXISTS stop_times CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS route_types CASCADE;
DROP TABLE IF EXISTS route_category_lookup CASCADE;
DROP TABLE IF EXISTS stops CASCADE;
DROP TABLE IF EXISTS shapes CASCADE;
DROP TABLE IF EXISTS calendar_dates CASCADE;
DROP TABLE IF EXISTS calendar CASCADE;
DROP TABLE IF EXISTS agency CASCADE;
DROP TABLE IF EXISTS wheelchair_boardings CASCADE;
DROP TABLE IF EXISTS wheelchair_accessibilities CASCADE;
DROP TABLE IF EXISTS bikes_allowed_types CASCADE;
DROP TABLE IF EXISTS location_types CASCADE;
DROP TABLE IF EXISTS exception_types CASCADE;

-- =========================================================================
-- SZÓTÁRTÁBLÁK (Lookup tables a kódok jelentéséhez)
-- =========================================================================

-- 1. Megállók akadálymentesítése (wheelchair_boarding)
CREATE TABLE wheelchair_boardings (
    code SMALLINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO wheelchair_boardings (code, name, description) VALUES
(0, 'Nincs információ', 'Nincs megadva információ a megálló akadálymentesítéséről.'),
(1, 'Akadálymentes', 'A megálló alkalmas kerekesszékes utasok számára.'),
(2, 'Nem akadálymentes', 'A megálló nem kerekesszék-barát.');

-- 2. Járművek akadálymentesítése (wheelchair_accessible)
CREATE TABLE wheelchair_accessibilities (
    code SMALLINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO wheelchair_accessibilities (code, name, description) VALUES
(0, 'Nincs információ', 'Nincs információ arról, hogy a járat akadálymentes-e.'),
(1, 'Akadálymentes', 'A jármű alkalmas legalább egy kerekesszékes utas szállítására.'),
(2, 'Nem akadálymentes', 'A járaton nem biztosított a kerekesszékes szállítás.');

-- 3. Kerékpárszállítás (bikes_allowed)
CREATE TABLE bikes_allowed_types (
    code SMALLINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO bikes_allowed_types (code, name, description) VALUES
(0, 'Nincs információ', 'Nincs információ a kerékpárszállításról.'),
(1, 'Megengedett', 'A járművön megengedett a kerékpárok szállítása.'),
(2, 'Nem engedélyezett', 'A járat nem szállít kerékpárt.');

-- 4. Megálló típusa (location_type)
CREATE TABLE location_types (
    code INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO location_types (code, name, description) VALUES
(0, 'Megállóhely (Stop)', 'Fizikai megálló, ahol az utasok fel- és leszállhatnak.'),
(1, 'Állomás / Csomópont (Station)', 'Fizikai terület, amely több megállót/peront fog össze.'),
(2, 'Bejárat / Kijárat (Entrance/Exit)', 'Az állomás bejárata vagy kijárata.'),
(3, 'Átszállási csomópont (Generic node)', 'Elágazási pont az állomáson belül.'),
(4, 'Beszállási zóna (Boarding area)', 'A peron egy specifikus pontja.');

-- 5. Naptár kivételek típusa (exception_type)
CREATE TABLE exception_types (
    code INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO exception_types (code, name, description) VALUES
(1, 'Hozzáadott nap (Added)', 'A szolgáltatás ezen a napon közlekedik (kiegészítésként).'),
(2, 'Törölt nap (Removed)', 'A szolgáltatás ezen a napon NEM közlekedik (kivételként).');

-- 6. Járat-típusok szótártáblája (route_type)
CREATE TABLE route_types (
    route_type INT PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL,
    description TEXT
);
INSERT INTO route_types (route_type, type_name, description) VALUES
(0, 'Villamos', 'Tram, Streetcar, Light rail'),
(1, 'Metró', 'Subway, Metro'),
(2, 'Vasút', 'Rail'),
(3, 'Busz', 'Bus'),
(4, 'Komp', 'Ferry'),
(5, 'Kábeles villamos', 'Cable tram'),
(6, 'Libegő', 'Aerial lift'),
(7, 'Sikló', 'Funicular'),
(11, 'Trolibusz', 'Trolleybus'),
(12, 'Egysínű vasút', 'Monorail'),
(100, 'Vasúti szolgáltatás', 'Railway Service'),
(109, 'Elővárosi vasút / HÉV', 'Suburban Railway / Commuter Rail');

-- 7. ÚJ: route_sort_order kategória lookup tábla (csoportosításhoz/szűréshez)
CREATE TABLE route_category_lookup (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    min_order INT NOT NULL,
    max_order INT NOT NULL
);
INSERT INTO route_category_lookup (category_name, min_order, max_order) VALUES
('Metró és HÉV', 0, 11),
('Villamos', 12, 21),
('Nappali autóbusz', 22, 329),
('Éjszakai autóbusz', 330, 999);


-- =========================================================================
-- FŐ GTFS TÁBLÁK
-- =========================================================================

-- 8. Agency (Szolgáltatók)
CREATE TABLE agency (
    agency_id VARCHAR(50) PRIMARY KEY,
    agency_name VARCHAR(255) NOT NULL,
    agency_url VARCHAR(255) NOT NULL,
    agency_timezone VARCHAR(50) NOT NULL,
    agency_lang VARCHAR(10),
    agency_phone VARCHAR(50)
);

-- 9. Routes (Járatok / Vonalak) - Kiegészítve route_sort_order-rel
CREATE TABLE routes (
    agency_id VARCHAR(50),
    route_id VARCHAR(50) PRIMARY KEY,
    route_short_name VARCHAR(50),
    route_long_name VARCHAR(255),
    route_type INT NOT NULL,
    route_desc TEXT,
    route_color VARCHAR(6),
    route_text_color VARCHAR(6),
    route_sort_order INT,
    FOREIGN KEY (agency_id) REFERENCES agency(agency_id),
    FOREIGN KEY (route_type) REFERENCES route_types(route_type)
);

-- 10. Calendar Dates (Kivételek a naptárból)
CREATE TABLE calendar_dates (
    service_id VARCHAR(100),
    date DATE NOT NULL,
    exception_type INT NOT NULL,
    PRIMARY KEY (service_id, date),
    FOREIGN KEY (exception_type) REFERENCES exception_types(code)
);

-- 11. Shapes (Nyomvonal pontjai)
CREATE TABLE shapes (
    shape_id VARCHAR(50),
    shape_pt_sequence INT NOT NULL,
    shape_pt_lat DECIMAL(9,6) NOT NULL,
    shape_pt_lon DECIMAL(9,6) NOT NULL,
    shape_dist_traveled DECIMAL(10,2),
    PRIMARY KEY (shape_id, shape_pt_sequence)
);

-- 12. Stops (Megállók)
CREATE TABLE stops (
    stop_id VARCHAR(50) PRIMARY KEY,
    stop_name VARCHAR(255) NOT NULL,
    stop_lat DECIMAL(9,6) NOT NULL,
    stop_lon DECIMAL(9,6) NOT NULL,
    stop_code VARCHAR(50),
    location_type INT DEFAULT 0,
    location_subtype VARCHAR(50),
    parent_station VARCHAR(50),
    wheelchair_boarding SMALLINT DEFAULT 0,
    FOREIGN KEY (parent_station) REFERENCES stops(stop_id),
    FOREIGN KEY (location_type) REFERENCES location_types(code),
    FOREIGN KEY (wheelchair_boarding) REFERENCES wheelchair_boardings(code)
);


-- 13. Trips (Indítások / Menetek)
CREATE TABLE trips (
    route_id VARCHAR(50) NOT NULL,
    trip_id VARCHAR(100) PRIMARY KEY,
    service_id VARCHAR(100) NOT NULL,
    trip_headsign VARCHAR(255),
    direction_id VARCHAR(50),
    block_id VARCHAR(50),
    shape_id VARCHAR(50),
    wheelchair_accessible SMALLINT DEFAULT 0,
    bikes_allowed SMALLINT DEFAULT 0,
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    FOREIGN KEY (wheelchair_accessible) REFERENCES wheelchair_accessibilities(code),
    FOREIGN KEY (bikes_allowed) REFERENCES bikes_allowed_types(code)
);

-- 14. Stop Times (Megállási és érkezési idők)
CREATE TABLE stop_times (
    trip_id VARCHAR(100) NOT NULL,
    stop_id VARCHAR(50) NOT NULL,
    arrival_time VARCHAR(8) NOT NULL,
    departure_time VARCHAR(8) NOT NULL,
    stop_sequence INT NOT NULL,
    stop_headsign VARCHAR(255),
    pickup_type INT DEFAULT 0,
    drop_off_type INT DEFAULT 0,
    shape_dist_traveled DECIMAL(10,2),
    PRIMARY KEY (trip_id, stop_sequence),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- Indexek a gyorsabb kereséshez
CREATE INDEX idx_stop_times_stop ON stop_times(stop_id);
CREATE INDEX idx_trips_route ON trips(route_id);
CREATE INDEX idx_trips_service ON trips(service_id);
CREATE INDEX idx_stops_coords ON stops(stop_lat, stop_lon);