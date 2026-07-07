import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { api } from "../api";

export default function Traffic() {
  const [hourly, setHourly] = useState<{ hour: string; count: number }[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .hourly()
      .then((r) => {
        const data = Object.entries(r.hourly_counts)
          .map(([hour, count]) => ({ hour: `${hour}:00`, count }))
          .sort((a, b) => parseInt(a.hour) - parseInt(b.hour));
        setHourly(data);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const peak = hourly.reduce((best, cur) => (cur.count > best.count ? cur : best), {
    hour: "-",
    count: 0,
  });

  return (
    <>
      <h2 className="page-title">Traffic Analytics</h2>
      <p className="page-sub">Hourly mobility patterns from aggregated GPS activity</p>

      {error && <p className="error">{error}</p>}

      <div className="cards">
        <div className="card">
          <div className="label">Peak Hour</div>
          <div className="value">{peak.hour}</div>
        </div>
        <div className="card">
          <div className="label">Peak Activity</div>
          <div className="value">{peak.count.toLocaleString()}</div>
        </div>
      </div>

      <div className="panel">
        <h3>Activity by Hour of Day</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={hourly}>
            <CartesianGrid stroke="#2d3a4f" strokeDasharray="3 3" />
            <XAxis dataKey="hour" stroke="#8b9cb3" interval={1} />
            <YAxis stroke="#8b9cb3" />
            <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
            <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
