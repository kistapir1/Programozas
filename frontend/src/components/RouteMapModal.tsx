import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export interface MapLegData {
  route_short_name: string;
  route_long_name: string;
  transport_mode: string;
  operator: string;
  origin_station: string;
  origin_lat?: number | null;
  origin_lon?: number | null;
  departure_time: string;
  destination_station: string;
  destination_lat?: number | null;
  destination_lon?: number | null;
  arrival_time: string;
  walk_seconds_before?: number;
  transfer_station?: string;
  shape_points?: [number, number][];
}

export interface MapScheduleResult {
  trip_id: number | string;
  route_short_name: string;
  route_long_name: string;
  transport_mode: string;
  operator: string;
  origin_station: string;
  origin_lat?: number | null;
  origin_lon?: number | null;
  departure_time: string;
  destination_station: string;
  destination_lat?: number | null;
  destination_lon?: number | null;
  arrival_time: string;
  transfers?: number;
  shape_points?: [number, number][];
  legs?: MapLegData[];
}

interface RouteMapModalProps {
  route: MapScheduleResult | null;
  onClose: () => void;
}

const LEG_COLORS = ["#2563eb", "#059669", "#7c3aed", "#db2777"];

function createPinIcon(label: string, color: string) {
  return L.divIcon({
    className: "route-map-pin",
    html: `<div style="
      background:${color};
      color:#fff;
      width:28px;
      height:28px;
      border-radius:50%;
      border:2px solid #fff;
      box-shadow:0 2px 6px rgba(0,0,0,0.35);
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:10px;
      font-weight:700;
      font-family:sans-serif;
    ">${label}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function sliceShape(
  shape: [number, number][],
  start?: [number, number] | null,
  end?: [number, number] | null
): [number, number][] {
  if (!shape || shape.length < 2) return [];
  if (!start || !end) return [];

  const nearestIndex = (pt: [number, number]) => {
    let bestIdx = 0;
    let bestDist = Infinity;
    for (let i = 0; i < shape.length; i++) {
      const dLat = shape[i][0] - pt[0];
      const dLon = shape[i][1] - pt[1];
      const dist = dLat * dLat + dLon * dLon;
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = i;
      }
    }
    return bestIdx;
  };

  const i1 = nearestIndex(start);
  const i2 = nearestIndex(end);

  if (i1 === i2) {
    return [start, end];
  }

  const sliced = i1 < i2 ? shape.slice(i1, i2 + 1) : shape.slice(i2, i1 + 1).reverse();
  return [start, ...sliced.slice(1, -1), end];
}

export default function RouteMapModal({ route, onClose }: RouteMapModalProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!route || !containerRef.current) return;

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map = L.map(containerRef.current, {
      center: [47.4979, 19.0402],
      zoom: 12,
    });
    mapRef.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    const legs: MapLegData[] =
      route.legs && route.legs.length > 0
        ? route.legs
        : [
            {
              route_short_name: route.route_short_name,
              route_long_name: route.route_long_name,
              transport_mode: route.transport_mode,
              operator: route.operator,
              origin_station: route.origin_station,
              origin_lat: route.origin_lat,
              origin_lon: route.origin_lon,
              departure_time: route.departure_time,
              destination_station: route.destination_station,
              destination_lat: route.destination_lat,
              destination_lon: route.destination_lon,
              arrival_time: route.arrival_time,
              shape_points: route.shape_points,
            },
          ];

    const boundsPoints: L.LatLngExpression[] = [];
    let prevEndPt: [number, number] | null = null;

    legs.forEach((leg, idx) => {
      const color = LEG_COLORS[idx % LEG_COLORS.length];
      const rawStartPt: [number, number] | null =
        leg.origin_lat != null && leg.origin_lon != null
          ? [leg.origin_lat, leg.origin_lon]
          : idx === 0 && route.origin_lat != null && route.origin_lon != null
          ? [route.origin_lat, route.origin_lon]
          : null;

      const startPt: [number, number] | null = rawStartPt ?? (idx > 0 ? prevEndPt : null);

      const endPt: [number, number] | null =
        leg.destination_lat != null && leg.destination_lon != null
          ? [leg.destination_lat, leg.destination_lon]
          : idx === legs.length - 1 && route.destination_lat != null && route.destination_lon != null
          ? [route.destination_lat, route.destination_lon]
          : null;

      let coords = sliceShape(leg.shape_points ?? [], startPt, endPt);
      if (coords.length < 2 && startPt && endPt) {
        coords = [startPt, endPt];
      }

      if (coords.length >= 2) {
        L.polyline(coords, { color, weight: 5, opacity: 0.9 })
          .bindPopup(
            `<strong>${leg.route_short_name}</strong> (${leg.transport_mode})<br/>${leg.origin_station} (${leg.departure_time}) → ${leg.destination_station} (${leg.arrival_time})`
          )
          .addTo(map);
        coords.forEach((pt) => boundsPoints.push(pt));
      }

      if (idx === 0 && startPt) {
        boundsPoints.push(startPt);
        L.marker(startPt, { icon: createPinIcon("IND", "#16a34a") })
          .bindPopup(
            `<strong>Indulás: ${leg.origin_station}</strong><br/>Idő: ${leg.departure_time}<br/>Járat: ${leg.route_short_name}`
          )
          .addTo(map);
      }

      if (idx > 0) {
        const transferPt = startPt ?? prevEndPt;
        if (transferPt) {
          const prevLeg = legs[idx - 1];
          const transferLabel = leg.transfer_station || prevLeg.destination_station || leg.origin_station;
          const walkMin = leg.walk_seconds_before
            ? `<br/>Átszállás / séta: ~${Math.round(leg.walk_seconds_before / 60)} perc`
            : "";
          boundsPoints.push(transferPt);
          L.marker(transferPt, { icon: createPinIcon("ÁT", "#d97706") })
            .bindPopup(
              `<strong>Átszállás: ${transferLabel}</strong><br/>Leszállás (${prevLeg.route_short_name}): ${prevLeg.arrival_time}<br/>Felszállás (${leg.route_short_name}): ${leg.departure_time}${walkMin}`
            )
            .addTo(map);
        }
      }

      if (idx === legs.length - 1 && endPt) {
        boundsPoints.push(endPt);
        L.marker(endPt, { icon: createPinIcon("CÉL", "#dc2626") })
          .bindPopup(
            `<strong>Érkezés: ${leg.destination_station}</strong><br/>Idő: ${leg.arrival_time}`
          )
          .addTo(map);
      }
      if (endPt) {
        prevEndPt = endPt;
      }
    });

    if (boundsPoints.length > 0) {
      map.fitBounds(L.latLngBounds(boundsPoints), { padding: [40, 40] });
    }

    const t = setTimeout(() => map.invalidateSize(), 150);
    return () => {
      clearTimeout(t);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [route]);

  if (!route) return null;

  return (
    <div className="route-modal-backdrop" onClick={onClose}>
      <div
        className="route-modal-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="route-modal-header">
          <div>
            <h3 className="route-modal-title">
              {route.origin_station} → {route.destination_station} ({route.departure_time} –{" "}
              {route.arrival_time})
            </h3>
            <p className="route-modal-subtitle">
              {route.route_short_name} •{" "}
              {(route.transfers ?? (route.legs ? route.legs.length - 1 : 0)) === 0
                ? "Közvetlen"
                : `${route.transfers ?? (route.legs ? route.legs.length - 1 : 0)} átszállás`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="route-modal-close-btn"
          >
            ✕ Bezárás
          </button>
        </div>
        <div ref={containerRef} className="route-modal-map" />
      </div>
    </div>
  );
}