import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api, ODFlow } from "../api";

export default function ODMatrix() {
  const [flows, setFlows] = useState<ODFlow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.odMatrix().then((r) => setFlows(r.flows)).catch((e) => setError(String(e)));
  }, []);

  const chartData = flows.slice(0, 10).map((f) => ({
    name: `${f.origin.split("(")[1]?.slice(0, 8) ?? f.origin} → ${f.destination.split("(")[1]?.slice(0, 8) ?? f.destination}`,
    trips: f.trip_count,
  }));

  return (
    <>
      <h2 className="page-title">Origin–Destination Matrix</h2>
      <p className="page-sub">Top zone-to-zone trip flows across Beijing</p>

      {error && <p className="error">{error}</p>}

      <div className="panel">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" stroke="#8b9cb3" />
            <YAxis type="category" dataKey="name" width={140} stroke="#8b9cb3" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
            <Bar dataKey="trips" fill="#10b981" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Origin</th>
              <th>Destination</th>
              <th>Trips</th>
            </tr>
          </thead>
          <tbody>
            {flows.map((f, i) => (
              <tr key={i}>
                <td>{f.origin}</td>
                <td>{f.destination}</td>
                <td>{f.trip_count.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
