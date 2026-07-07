import { useEffect, useState } from "react";
import { LivePing, LiveTrip, liveWsUrl } from "../api";

interface LiveState {
  trip: LiveTrip | null;
  pings: LivePing[];
  etaMinutes: number | null;
  remainingKm: number | null;
  etaSource: string | null;
  routeGeometry: [number, number][] | null;
  status: string;
  connected: boolean;
  lastMessage: string;
  riderName: string | null;
}

export function useLiveTrip(tripId: string | null) {
  const [state, setState] = useState<LiveState>({
    trip: null,
    pings: [],
    etaMinutes: null,
    remainingKm: null,
    etaSource: null,
    routeGeometry: null,
    status: "pending",
    connected: false,
    lastMessage: "",
    riderName: null,
  });
  const wsRef = { current: null as WebSocket | null };

  useEffect(() => {
    if (!tripId) return;

    const ws = new WebSocket(liveWsUrl(tripId));
    wsRef.current = ws;

    ws.onopen = () => setState((s) => ({ ...s, connected: true }));
    ws.onclose = () => setState((s) => ({ ...s, connected: false }));

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "connected") {
        setState((s) => ({
          ...s,
          trip: data.trip,
          pings: data.history || [],
          etaMinutes: data.trip?.eta_minutes ?? null,
          remainingKm: data.trip?.remaining_km ?? null,
          status: data.trip?.status ?? "pending",
          riderName: data.trip?.rider_name ?? null,
        }));
      } else if (data.type === "location_update") {
        setState((s) => ({
          ...s,
          pings: [...s.pings, data.ping],
          etaMinutes: data.eta_minutes,
          remainingKm: data.remaining_km,
          etaSource: data.eta_source ?? null,
          routeGeometry: data.route_geometry ?? s.routeGeometry,
          status: data.status,
          lastMessage: `Updated ${new Date(data.ping.recorded_at).toLocaleTimeString()}`,
        }));
      } else if (data.type === "trip_completed") {
        setState((s) => ({
          ...s,
          pings: data.ping ? [...s.pings, data.ping] : s.pings,
          etaMinutes: 0,
          remainingKm: 0,
          status: "completed",
          lastMessage: data.message || "Arrived!",
          riderName: data.rider_name ?? s.riderName,
        }));
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [tripId]);

  return state;
}
