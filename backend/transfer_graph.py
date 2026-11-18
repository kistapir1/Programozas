"""
transfer_graph.py – Átszállási gráf (transfer graph) a Budapest közlekedési hálózathoz
=======================================================================================
Három forrásból épít átszállási kapcsolatokat:
  1. parent_station  – azonos parent_station-nel rendelkező megállók (120 s)
  2. pathways        – a pathways tábla (from_stop_id → to_stop_id, traversal_time)
  3. hasonló név     – a megálló neve csak „ M", „ H" vagy „ M+H" utótagban
                       különbözik ÉS földrajzilag közel vannak (< 0.005°) → 180 s

Csak location_type = 0 / NULL megállók, amelyeknek van stop_times bejegyzése.
Singleton cache: TransferGraph.instance()
"""

from __future__ import annotations

import re
import threading
from collections import defaultdict
from typing import ClassVar

from database import get_db_connection


class TransferGraph:
    """Lazy-singleton átszállási gráf."""

    _instance: ClassVar[TransferGraph | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # ---- singleton -------------------------------------------------------
    @classmethod
    def instance(cls) -> TransferGraph:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- init & build ----------------------------------------------------
    def __init__(self) -> None:
        # stop_id  →  list[(target_stop_id, walk_seconds)]
        self._graph: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self._build()

    # Regex: alap_név  +  opcionális utótag  ( M | H | M+H )
    _SUFFIX_RE = re.compile(r"^(.+?)(?:\s+(?:M\+H|M|H))?$")

    def _build(self) -> None:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Az érvényes megállók halmaza (location_type=0 vagy NULL, van stop_times)
        cur.execute(
            """
            SELECT DISTINCT s.stop_id, s.stop_name, s.stop_lat, s.stop_lon,
                   s.parent_station
            FROM stops s
            WHERE (s.location_type = 0 OR s.location_type IS NULL)
              AND EXISTS (
                  SELECT 1 FROM stop_times st WHERE st.stop_id = s.stop_id
              )
            """
        )
        rows = cur.fetchall()

        valid_ids: set[str] = set()
        stop_info: dict[str, dict] = {}  # stop_id → {name, lat, lon, parent}

        for r in rows:
            sid = r["stop_id"]
            valid_ids.add(sid)
            stop_info[sid] = {
                "name": r["stop_name"],
                "lat": float(r["stop_lat"]),
                "lon": float(r["stop_lon"]),
                "parent": r["parent_station"],
            }

        # ----- 1) parent_station kapcsolatok (120 s) -----------------------
        parent_groups: dict[str, list[str]] = defaultdict(list)
        for sid, info in stop_info.items():
            ps = info["parent"]
            if ps:
                parent_groups[ps].append(sid)

        for _parent, children in parent_groups.items():
            for i, a in enumerate(children):
                for b in children[i + 1 :]:
                    self._add_edge(a, b, 120)

        # ----- 2) pathways (traversal_time) --------------------------------
        cur.execute(
            """
            SELECT from_stop_id, to_stop_id, traversal_time, is_bidirectional
            FROM pathways
            """
        )
        for pw in cur.fetchall():
            f, t = pw["from_stop_id"], pw["to_stop_id"]
            tt = int(pw["traversal_time"])
            if f in valid_ids and t in valid_ids:
                self._add_edge_directed(f, t, tt)
                if pw["is_bidirectional"] == 1:
                    self._add_edge_directed(t, f, tt)

        # ----- 3) hasonló név (M / H / M+H utótag) + közelség (180 s) -----
        base_groups: dict[str, list[str]] = defaultdict(list)
        for sid, info in stop_info.items():
            m = self._SUFFIX_RE.match(info["name"])
            if m:
                base = m.group(1).strip()
                base_groups[base].append(sid)

        for _base, group in base_groups.items():
            if len(group) < 2:
                continue
            for i, a in enumerate(group):
                for b in group[i + 1 :]:
                    # Csak ha valóban eltérő megállók (más stop_id)
                    if a == b:
                        continue
                    ia, ib = stop_info[a], stop_info[b]
                    if (
                        abs(ia["lat"] - ib["lat"]) < 0.005
                        and abs(ia["lon"] - ib["lon"]) < 0.005
                    ):
                        self._add_edge(a, b, 180)

        cur.close()
        conn.close()

        print(
            f"[TransferGraph] Gráf felépítve: {len(valid_ids)} megálló, "
            f"{sum(len(v) for v in self._graph.values())} él"
        )

    # ---- helpers ---------------------------------------------------------
    def _add_edge(self, a: str, b: str, seconds: int) -> None:
        """Kétirányú él hozzáadása (duplikáció-mentes, minimum-idő)."""
        self._add_edge_directed(a, b, seconds)
        self._add_edge_directed(b, a, seconds)

    def _add_edge_directed(self, src: str, dst: str, seconds: int) -> None:
        """Egyirányú él – ha már létezik, a kisebb walk_seconds marad."""
        for idx, (existing_dst, existing_sec) in enumerate(self._graph[src]):
            if existing_dst == dst:
                if seconds < existing_sec:
                    self._graph[src][idx] = (dst, seconds)
                return
        self._graph[src].append((dst, seconds))

    # ---- public API ------------------------------------------------------
    def get_transfers(self, stop_id: str) -> list[tuple[str, int]]:
        """Visszaadja az elérhető átszállásos megállókat és a sétaidőt (s)."""
        return self._graph.get(stop_id, [])
