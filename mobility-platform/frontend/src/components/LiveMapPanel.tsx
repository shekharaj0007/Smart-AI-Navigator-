import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import { LivePing, LiveTrip } from "../api";

function FitLiveBounds({
  lat,
  lon,
  destLat,
  destLon,
}: {
  lat: number;
  lon: number;
  destLat: number;
  destLon: number;
}) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(
      [
        [Math.min(lat, destLat), Math.min(lon, destLon)],
        [Math.max(lat, destLat), Math.max(lon, destLon)],
      ],
      { padding: [40, 40] }
    );
  }, [map, lat, lon, destLat, destLon]);
  return null;
}

interface Props {
  trip: LiveTrip | null;
  pings: LivePing[];
  routeGeometry?: [number, number][] | null;
  height?: number;
}

export default function LiveMapPanel({ trip, pings, routeGeometry, height = 480 }: Props) {
  const latest = pings[pings.length - 1];
  const trail = useMemo(
    () => pings.map((p) => [p.latitude, p.longitude] as [number, number]),
    [pings]
  );

  const centerLat = latest?.latitude ?? trip?.origin_lat ?? 39.904;
  const centerLon = latest?.longitude ?? trip?.origin_lon ?? 116.407;

  return (
    <div className="map-container" style={{ height }}>
      <MapContainer center={[centerLat, centerLon]} zoom={14} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="OSM"
        />
        {trip && (
          <>
            <CircleMarker
              center={[trip.origin_lat, trip.origin_lon]}
              pathOptions={{ color: "#8b5cf6", fillColor: "#8b5cf6", fillOpacity: 0.7 }}
              radius={6}
            />
            <CircleMarker
              center={[trip.dest_lat, trip.dest_lon]}
              pathOptions={{ color: "#10b981", fillColor: "#10b981", fillOpacity: 0.9 }}
              radius={9}
            />
            <FitLiveBounds
              lat={centerLat}
              lon={centerLon}
              destLat={trip.dest_lat}
              destLon={trip.dest_lon}
            />
          </>
        )}
        {routeGeometry && routeGeometry.length > 1 && (
          <Polyline positions={routeGeometry} color="#f59e0b" weight={5} opacity={0.85} dashArray="8 4" />
        )}
        {trail.length > 1 && <Polyline positions={trail} color="#3b82f6" weight={4} opacity={0.75} />}
        {latest && (
          <CircleMarker
            center={[latest.latitude, latest.longitude]}
            pathOptions={{ color: "#3b82f6", fillColor: "#3b82f6", fillOpacity: 1 }}
            radius={11}
          />
        )}
      </MapContainer>
    </div>
  );
}
