import { useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer } from "react-leaflet";
import { api, LivePing } from "../api";
import { copyShareLink, shareTrackUrl } from "../utils/share";

export default function RiderApp() {
  const [riderName, setRiderName] = useState("Rider 1");
  const [destLat, setDestLat] = useState("39.9042");
  const [destLon, setDestLon] = useState("116.4074");
  const [tripId, setTripId] = useState<string | null>(null);
  const [tracking, setTracking] = useState(false);
  const [error, setError] = useState("");
  const [pings, setPings] = useState<LivePing[]>([]);
  const [etaMinutes, setEtaMinutes] = useState<number | null>(null);
  const [remainingKm, setRemainingKm] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const watchIdRef = useRef<number | null>(null);
  const lastSentRef = useRef(0);

  const startTrip = () => {
    setError("");
    if (!navigator.geolocation) {
      setError("Geolocation not supported in this browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const { trip } = await api.createLiveTrip({
            rider_name: riderName,
            origin_lat: latitude,
            origin_lon: longitude,
            dest_lat: parseFloat(destLat),
            dest_lon: parseFloat(destLon),
            source_type: "real",
          });
          setTripId(trip.id);
          setTracking(true);
          const update = await api.sendLivePing(trip.id, { latitude, longitude, accuracy_m: pos.coords.accuracy });
          setPings([update.ping]);
          setEtaMinutes(update.eta_minutes);
          setRemainingKm(update.remaining_km);
        } catch (e) {
          setError(String(e));
        }
      },
      (e) => setError(`GPS error: ${e.message}`),
      { enableHighAccuracy: true }
    );
  };

  useEffect(() => {
    if (!tracking || !tripId) return;

    watchIdRef.current = navigator.geolocation.watchPosition(
      async (pos) => {
        const now = Date.now();
        if (now - lastSentRef.current < 3000) return;
        lastSentRef.current = now;

        const { latitude, longitude, speed, accuracy } = pos.coords;
        const speedKmh = speed != null && speed >= 0 ? speed * 3.6 : undefined;
        try {
          const update = await api.sendLivePing(tripId, {
            latitude,
            longitude,
            speed_kmh: speedKmh,
            accuracy_m: accuracy ?? undefined,
          });
          setPings((prev) => [...prev, update.ping]);
          setEtaMinutes(update.eta_minutes);
          setRemainingKm(update.remaining_km);
          if (update.trip.status === "completed") setTracking(false);
        } catch (e) {
          setError(String(e));
        }
      },
      (e) => setError(`GPS error: ${e.message}`),
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 }
    );

    return () => {
      if (watchIdRef.current != null) navigator.geolocation.clearWatch(watchIdRef.current);
    };
  }, [tracking, tripId]);

  const stopTrip = async () => {
    if (tripId) await api.completeLiveTrip(tripId);
    setTracking(false);
    if (watchIdRef.current != null) navigator.geolocation.clearWatch(watchIdRef.current);
  };

  const latest = pings[pings.length - 1];
  const route = pings.map((p) => [p.latitude, p.longitude] as [number, number]);
  const mapCenter: [number, number] = latest
    ? [latest.latitude, latest.longitude]
    : [parseFloat(destLat) || 39.904, parseFloat(destLon) || 116.407];

  return (
    <>
      <h2 className="page-title">Rider App</h2>
      <p className="page-sub">Real GPS from your device — share Trip ID with tracker (Option B)</p>

      {!tripId ? (
        <div className="panel">
          <div className="live-form">
            <label>Rider name<input value={riderName} onChange={(e) => setRiderName(e.target.value)} /></label>
            <label>Destination lat<input value={destLat} onChange={(e) => setDestLat(e.target.value)} /></label>
            <label>Destination lon<input value={destLon} onChange={(e) => setDestLon(e.target.value)} /></label>
          </div>
          <p className="muted">Uses your browser GPS. Allow location permission when prompted.</p>
          <button type="button" onClick={startTrip} style={{ marginTop: "1rem" }}>Start delivery trip</button>
        </div>
      ) : (
        <>
          <div className="cards">
            <div className="card"><div className="label">Trip ID (share this)</div><div className="value" style={{ fontSize: "0.95rem" }}>{tripId}</div></div>
            <div className="card"><div className="label">ETA to destination</div><div className="value">{etaMinutes != null ? `${etaMinutes} min` : "—"}</div></div>
            <div className="card"><div className="label">Remaining</div><div className="value">{remainingKm != null ? `${remainingKm} km` : "—"}</div></div>
            <div className="card"><div className="label">GPS pings sent</div><div className="value">{pings.length}</div></div>
          </div>

          <div className="panel">
            <p>
              <strong>Share tracking link:</strong>{" "}
              <a href={shareTrackUrl(tripId)} target="_blank" rel="noreferrer">{shareTrackUrl(tripId)}</a>
            </p>
            <div className="live-row" style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  const ok = await copyShareLink(tripId);
                  setCopied(ok);
                  setTimeout(() => setCopied(false), 2000);
                }}
              >
                {copied ? "Link copied!" : "Copy share link"}
              </button>
              {tracking ? (
                <button type="button" onClick={stopTrip} style={{ background: "#ef4444", borderColor: "#ef4444" }}>
                  End trip
                </button>
              ) : (
                <span style={{ color: "#10b981" }}>Trip completed</span>
              )}
            </div>
          </div>

          <div className="panel map-container">
            <MapContainer center={mapCenter} zoom={15} style={{ height: "100%", width: "100%" }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OSM" />
              <CircleMarker center={[parseFloat(destLat), parseFloat(destLon)]} pathOptions={{ color: "#10b981", fillColor: "#10b981", fillOpacity: 0.8 }} radius={8} />
              {route.length > 1 && <Polyline positions={route} color="#3b82f6" weight={4} />}
              {latest && <CircleMarker center={[latest.latitude, latest.longitude]} pathOptions={{ color: "#3b82f6", fillColor: "#3b82f6", fillOpacity: 1 }} radius={10} />}
            </MapContainer>
          </div>
        </>
      )}

      {error && <p className="error">{error}</p>}
    </>
  );
}
