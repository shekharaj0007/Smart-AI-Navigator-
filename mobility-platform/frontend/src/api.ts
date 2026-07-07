const API = "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  health: () => fetchJson<{ status: string; data_ready: boolean }>("/health"),
  stats: () => fetchJson<Record<string, unknown>>("/stats"),
  users: () => fetchJson<{ users: string[]; count: number }>("/users"),
  userTrips: (userId: string) =>
    fetchJson<{ trips: Trip[] }>(`/users/${userId}/trajectories?limit=30`),
  trajectory: (tripId: string) =>
    fetchJson<{ points: GPSPoint[]; stats: Record<string, unknown> }>(
      `/trajectory/${encodeURIComponent(tripId)}`
    ),
  heatmap: () => fetchJson<{ cells: HeatCell[] }>("/heatmap"),
  odMatrix: () => fetchJson<{ flows: ODFlow[] }>("/od-matrix?top_n=30"),
  hourly: () => fetchJson<{ hourly_counts: Record<string, number> }>("/traffic/hourly"),
  modes: () => fetchJson<{ modes: Record<string, number>; percentages: Record<string, number> }>(
    "/transport-modes"
  ),
  mlMetrics: () => fetchJson<Record<string, unknown>>("/ml/metrics"),
  chat: (question: string) =>
    postJson<{ answer: string; chart?: { type: string; data: unknown } }>("/chat", { question }),

  // Live tracking
  createLiveTrip: (body: CreateLiveTripBody) =>
    postJson<{ trip: LiveTrip }>("/live/trips", body),
  listLiveTrips: (status?: string) =>
    fetchJson<{ trips: LiveTrip[] }>(`/live/trips${status ? `?status=${status}` : ""}`),
  getLiveTrip: (tripId: string) =>
    fetchJson<{ trip: LiveTrip; simulating: boolean }>(`/live/trips/${tripId}`),
  getLiveHistory: (tripId: string) =>
    fetchJson<{ pings: LivePing[] }>(`/live/trips/${tripId}/history`),
  sendLivePing: (tripId: string, body: LivePingBody) =>
    postJson<LiveUpdate>(`/live/trips/${tripId}/ping`, body),
  simulateTrip: (tripId: string, geolifeTripId: string, intervalSec = 2) =>
    postJson<{ message: string }>(`/live/trips/${tripId}/simulate`, {
      geolife_trip_id: geolifeTripId,
      interval_sec: intervalSec,
    }),
  completeLiveTrip: (tripId: string) =>
    postJson<{ trip: LiveTrip }>(`/live/trips/${tripId}/complete`, {}),
};

export function liveWsUrl(tripId: string): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/live/${encodeURIComponent(tripId)}`;
}

export interface GPSPoint {
  latitude: number;
  longitude: number;
  timestamp: string;
  altitude_m?: number;
  transport_mode?: string | null;
}

export interface Trip {
  trip_id: string;
  user_id: string;
  start_time: string;
  end_time: string;
  point_count: number;
  duration_seconds: number;
  transport_mode?: string | null;
}

export interface HeatCell {
  latitude: number;
  longitude: number;
  count: number;
}

export interface ODFlow {
  origin: string;
  destination: string;
  trip_count: number;
}

export interface LiveTrip {
  id: string;
  rider_name: string;
  source_type: string;
  geolife_trip_id?: string | null;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  status: string;
  eta_minutes?: number | null;
  remaining_km?: number | null;
  started_at?: string | null;
  arrived_at?: string | null;
  created_at: string;
  latest_ping?: LivePing | null;
  ping_count?: number;
}

export interface LivePing {
  id?: number;
  trip_id: string;
  latitude: number;
  longitude: number;
  speed_kmh?: number | null;
  accuracy_m?: number | null;
  recorded_at: string;
}

export interface CreateLiveTripBody {
  rider_name: string;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  source_type?: string;
}

export interface LivePingBody {
  latitude: number;
  longitude: number;
  speed_kmh?: number;
  accuracy_m?: number;
}

export interface LiveUpdate {
  trip: LiveTrip;
  ping: LivePing;
  eta_minutes: number;
  remaining_km: number;
  avg_speed_kmh?: number;
}
