import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, useMap } from "react-leaflet";
import { api, GPSPoint, Trip } from "../api";

function FitBounds({ points }: { points: GPSPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length < 2) return;
    const lats = points.map((p) => p.latitude);
    const lons = points.map((p) => p.longitude);
    map.fitBounds([
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ]);
  }, [map, points]);
  return null;
}

export default function MapExplorer() {
  const [users, setUsers] = useState<string[]>([]);
  const [userId, setUserId] = useState("010");
  const [trips, setTrips] = useState<Trip[]>([]);
  const [selectedTrip, setSelectedTrip] = useState("");
  const [points, setPoints] = useState<GPSPoint[]>([]);
  const [heatmap, setHeatmap] = useState<{ latitude: number; longitude: number; count: number }[]>([]);
  const [showHeat, setShowHeat] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.users().then((u) => setUsers(u.users)).catch((e) => setError(String(e)));
    api.heatmap().then((h) => setHeatmap(h.cells.slice(0, 200))).catch(() => {});
  }, []);

  useEffect(() => {
    if (!userId) return;
    api.userTrips(userId).then((r) => {
      setTrips(r.trips);
      if (r.trips[0]) setSelectedTrip(r.trips[0].trip_id);
    }).catch((e) => setError(String(e)));
  }, [userId]);

  useEffect(() => {
    if (!selectedTrip) return;
    api.trajectory(selectedTrip).then((r) => setPoints(r.points)).catch((e) => setError(String(e)));
  }, [selectedTrip]);

  const positions = useMemo(
    () => points.map((p) => [p.latitude, p.longitude] as [number, number]),
    [points]
  );

  const maxHeat = Math.max(...heatmap.map((h) => h.count), 1);

  return (
    <>
      <h2 className="page-title">Map Explorer</h2>
      <p className="page-sub">Visualize GPS trajectories and density heatmap</p>

      <div className="panel" style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <label>
          User{" "}
          <select value={userId} onChange={(e) => setUserId(e.target.value)}>
            {users.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </label>
        <label>
          Trip{" "}
          <select value={selectedTrip} onChange={(e) => setSelectedTrip(e.target.value)}>
            {trips.map((t) => (
              <option key={t.trip_id} value={t.trip_id}>
                {t.trip_id.slice(-20)} ({t.point_count} pts)
              </option>
            ))}
          </select>
        </label>
        <label>
          <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
          {" "}Show heatmap overlay
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="panel map-container">
        <MapContainer center={[39.904, 116.407]} zoom={11} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {positions.length > 1 && (
            <>
              <Polyline positions={positions} color="#3b82f6" weight={4} opacity={0.85} />
              <FitBounds points={points} />
            </>
          )}
          {showHeat &&
            heatmap.map((h, i) => (
              <CircleMarker
                key={i}
                center={[h.latitude, h.longitude]}
                radius={Math.max(3, (h.count / maxHeat) * 12)}
                pathOptions={{
                  color: "#f59e0b",
                  fillColor: "#f59e0b",
                  fillOpacity: 0.35,
                  weight: 0,
                }}
              />
            ))}
        </MapContainer>
      </div>
    </>
  );
}
