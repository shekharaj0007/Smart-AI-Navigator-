import { useEffect, useState } from "react";
import { api } from "../api";
import LiveMapPanel from "../components/LiveMapPanel";
import { useArrivalNotification } from "../hooks/useArrivalNotification";
import { useLiveTrip } from "../hooks/useLiveTrip";
import { shareTrackUrl } from "../utils/share";

interface Props {
  tripId: string;
  compact?: boolean;
}

export default function ShareTrackPage({ tripId, compact = false }: Props) {
  const live = useLiveTrip(tripId);
  const notif = useArrivalNotification(live.status, live.riderName ?? live.trip?.rider_name, tripId);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!compact) document.title = `Track ${tripId} · Mobility Platform`;
  }, [tripId, compact]);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareTrackUrl(tripId));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const etaLabel =
    live.status === "completed"
      ? "Arrived"
      : live.etaMinutes != null
        ? `${live.etaMinutes} min`
        : "Calculating…";

  const content = (
    <>
      {notif.toast && (
        <div className="arrival-toast" role="alert">
          <span>{notif.toast}</span>
          <button type="button" onClick={notif.dismissToast}>×</button>
        </div>
      )}

      <div className="track-header">
        <div>
          <h2 className="page-title" style={{ marginBottom: "0.25rem" }}>
            {live.status === "completed" ? "Delivered" : "Live delivery tracking"}
          </h2>
          <p className="page-sub" style={{ margin: 0 }}>
            {live.trip?.rider_name ?? "Rider"} · {tripId}
            {live.connected && live.status !== "completed" && (
              <span className="live-dot"> · Live</span>
            )}
          </p>
        </div>
        <div className="track-actions">
          {notif.notifPermission === "default" && (
            <button type="button" className="btn-secondary" onClick={notif.requestPermission}>
              Enable alerts
            </button>
          )}
          <button type="button" onClick={copyLink}>{copied ? "Copied!" : "Copy link"}</button>
        </div>
      </div>

      <div className="cards">
        <div className="card eta-card">
          <div className="label">Time left</div>
          <div className="value">{etaLabel}</div>
        </div>
        <div className="card">
          <div className="label">Distance left</div>
          <div className="value">
            {live.remainingKm != null ? `${live.remainingKm} km` : "—"}
          </div>
        </div>
        <div className="card">
          <div className="label">Status</div>
          <div className="value" style={{ fontSize: "1.1rem", color: live.status === "completed" ? "#10b981" : "#3b82f6" }}>
            {live.status.replace("_", " ")}
          </div>
        </div>
        <div className="card">
          <div className="label">ETA source</div>
          <div className="value" style={{ fontSize: "0.95rem" }}>{live.etaSource ?? "—"}</div>
        </div>
      </div>

      {live.lastMessage && <p className="muted">{live.lastMessage}</p>}

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <LiveMapPanel
          trip={live.trip}
          pings={live.pings}
          routeGeometry={live.routeGeometry}
          height={compact ? 360 : 520}
        />
      </div>

      <div className="map-legend muted">
        <span><i className="dot blue" /> Rider path</span>
        <span><i className="dot orange" /> Road route (OSRM)</span>
        <span><i className="dot green" /> Destination</span>
      </div>

      {live.pings.length > 0 && (
        <div className="panel">
          <h3>Location log</h3>
          <div className="ping-table-wrap">
            <table>
              <thead>
                <tr><th>Timestamp</th><th>Lat</th><th>Lon</th><th>Speed</th></tr>
              </thead>
              <tbody>
                {[...live.pings].reverse().slice(0, 15).map((p, i) => (
                  <tr key={i}>
                    <td>{new Date(p.recorded_at).toLocaleString()}</td>
                    <td>{p.latitude.toFixed(5)}</td>
                    <td>{p.longitude.toFixed(5)}</td>
                    <td>{p.speed_kmh != null ? `${p.speed_kmh.toFixed(1)} km/h` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );

  if (compact) return content;

  return (
    <div className="share-page">
      <header className="share-topbar">
        <strong>Mobility Live Track</strong>
        <a href="/">← Back to platform</a>
      </header>
      <main className="share-main">{content}</main>
    </div>
  );
}

/** Standalone page — reads trip ID from URL /track/:id */
export function ShareTrackRoute() {
  const tripId = window.location.pathname.split("/track/")[1]?.split("/")[0]?.toUpperCase() ?? "";
  const [valid, setValid] = useState<boolean | null>(null);

  useEffect(() => {
    if (!tripId) {
      setValid(false);
      return;
    }
    api.getLiveTrip(tripId).then(() => setValid(true)).catch(() => setValid(false));
  }, [tripId]);

  if (!tripId || valid === false) {
    return (
      <div className="share-page">
        <main className="share-main">
          <h2>Trip not found</h2>
          <p className="muted">Invalid or expired tracking link.</p>
          <a href="/">Go home</a>
        </main>
      </div>
    );
  }

  if (valid === null) return <div className="share-page"><main className="share-main">Loading…</main></div>;

  return <ShareTrackPage tripId={tripId} />;
}
