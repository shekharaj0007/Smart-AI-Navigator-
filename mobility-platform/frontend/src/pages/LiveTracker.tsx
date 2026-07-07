import { useEffect, useState } from "react";
import { api } from "../api";
import ShareTrackPage from "./ShareTrackPage";

export default function LiveTracker() {
  const [tripIdInput, setTripIdInput] = useState("");
  const [activeTripId, setActiveTripId] = useState<string | null>(null);
  const [activeTrips, setActiveTrips] = useState<{ id: string; rider_name: string; status: string }[]>([]);
  const [simUser, setSimUser] = useState("010");
  const [simUsers, setSimUsers] = useState<string[]>(["010"]);
  const [simTrips, setSimTrips] = useState<{ trip_id: string; point_count: number }[]>([]);
  const [simTripId, setSimTripId] = useState("");
  const [creatingSim, setCreatingSim] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.users().then((r) => setSimUsers(r.users.slice(0, 20))).catch(() => {});
    api.listLiveTrips().then((r) =>
      setActiveTrips(r.trips.map((t) => ({ id: t.id, rider_name: t.rider_name, status: t.status })))
    ).catch(() => {});
  }, [activeTripId]);

  useEffect(() => {
    api.userTrips(simUser).then((r) => {
      setSimTrips(r.trips.map((t) => ({ trip_id: t.trip_id, point_count: t.point_count })));
      if (r.trips[0]) setSimTripId(r.trips[0].trip_id);
    }).catch(() => {});
  }, [simUser]);

  const track = () => {
    if (tripIdInput.trim()) setActiveTripId(tripIdInput.trim().toUpperCase());
  };

  const startSimulation = async () => {
    if (!simTripId) return;
    setCreatingSim(true);
    setError("");
    try {
      const traj = await api.trajectory(simTripId);
      const pts = traj.points;
      if (pts.length < 2) throw new Error("Trajectory too short");
      const first = pts[0];
      const last = pts[pts.length - 1];
      const { trip } = await api.createLiveTrip({
        rider_name: `Sim Rider (${simUser})`,
        origin_lat: first.latitude,
        origin_lon: first.longitude,
        dest_lat: last.latitude,
        dest_lon: last.longitude,
        source_type: "simulated",
      });
      await api.simulateTrip(trip.id, simTripId, 2);
      setActiveTripId(trip.id);
      setTripIdInput(trip.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setCreatingSim(false);
    }
  };

  return (
    <>
      <h2 className="page-title">Live Tracker</h2>
      <p className="page-sub">Blinkit-style tracking · OSRM road ETA · shareable links</p>

      <div className="panel live-controls">
        <div className="live-row">
          <input
            placeholder="Enter Trip ID e.g. TRIP-A1B2C3D4"
            value={tripIdInput}
            onChange={(e) => setTripIdInput(e.target.value)}
          />
          <button type="button" onClick={track}>Track</button>
        </div>
        {activeTrips.length > 0 && (
          <div className="live-row">
            <span className="muted">Recent trips:</span>
            {activeTrips.slice(0, 5).map((t) => (
              <button
                key={t.id}
                type="button"
                className="chip"
                onClick={() => { setActiveTripId(t.id); setTripIdInput(t.id); }}
              >
                {t.id} ({t.status})
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Simulate from Geolife (Option A)</h3>
        <div className="live-row">
          <label>
            User{" "}
            <select value={simUser} onChange={(e) => setSimUser(e.target.value)}>
              {simUsers.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </label>
          <label>
            Trip{" "}
            <select value={simTripId} onChange={(e) => setSimTripId(e.target.value)}>
              {simTrips.map((t) => (
                <option key={t.trip_id} value={t.trip_id}>
                  {t.trip_id.slice(-15)} ({t.point_count} pts)
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={startSimulation} disabled={creatingSim}>
            {creatingSim ? "Starting..." : "Start simulated delivery"}
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {activeTripId && <ShareTrackPage tripId={activeTripId} compact />}
    </>
  );
}
