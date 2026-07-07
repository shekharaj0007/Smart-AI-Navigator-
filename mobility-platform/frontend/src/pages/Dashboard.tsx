import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api";

export default function Dashboard() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [modes, setModes] = useState<Record<string, number>>({});
  const [ml, setMl] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.stats(), api.modes(), api.mlMetrics()])
      .then(([s, m, mlData]) => {
        setStats(s);
        setModes(m.modes);
        setMl(mlData);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading...</p>;

  const modeChart = Object.entries(modes).map(([name, value]) => ({ name, value }));

  return (
    <>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-sub">Geolife dataset overview and key metrics</p>

      <div className="cards">
        <StatCard label="Users" value={String(stats.users ?? 0)} />
        <StatCard label="Trips" value={Number(stats.trips ?? 0).toLocaleString()} />
        <StatCard label="GPS Points" value={Number(stats.gps_points ?? 0).toLocaleString()} />
        <StatCard label="Labeled Users" value={String(stats.labeled_users ?? 0)} />
        <StatCard
          label="ML Accuracy"
          value={ml?.accuracy ? `${(Number(ml.accuracy) * 100).toFixed(1)}%` : "N/A"}
        />
      </div>

      {modeChart.length > 0 && (
        <div className="panel">
          <h3>Transport Mode Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={modeChart}>
              <XAxis dataKey="name" stroke="#8b9cb3" />
              <YAxis stroke="#8b9cb3" />
              <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}
