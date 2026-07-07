import { useEffect, useState } from "react";
import { api } from "./api";
import Dashboard from "./pages/Dashboard";
import MapExplorer from "./pages/MapExplorer";
import ODMatrix from "./pages/ODMatrix";
import Traffic from "./pages/Traffic";
import Assistant from "./pages/Assistant";
import LiveTracker from "./pages/LiveTracker";
import RiderApp from "./pages/RiderApp";

type Page = "dashboard" | "map" | "od" | "traffic" | "assistant" | "live" | "rider";

const NAV: { id: Page; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "live", label: "Live Tracker" },
  { id: "rider", label: "Rider App" },
  { id: "map", label: "Map Explorer" },
  { id: "od", label: "OD Matrix" },
  { id: "traffic", label: "Traffic Analytics" },
  { id: "assistant", label: "AI Assistant" },
];

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [ready, setReady] = useState<boolean | null>(null);
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      try {
        const h = await api.health();
        if (cancelled) return;
        setBackendOnline(true);
        setReady(h.data_ready);
      } catch {
        if (cancelled) return;
        setBackendOnline(false);
        setReady(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>AI Mobility Intelligence Platform</h1>
        <nav>
          {NAV.map((n) => (
            <a
              key={n.id}
              href="#"
              className={`nav-link ${page === n.id ? "active" : ""}`}
              onClick={(e) => {
                e.preventDefault();
                setPage(n.id);
              }}
            >
              {n.label}
            </a>
          ))}
        </nav>
        {!backendOnline && (
          <p className="error" style={{ fontSize: "0.8rem", marginTop: "1rem" }}>
            Backend offline. Start API: python -m uvicorn app.main:app --port 8000
          </p>
        )}
        {backendOnline && ready === false && (
          <p className="error" style={{ fontSize: "0.8rem", marginTop: "1rem" }}>
            Data not processed yet. Run: python etl/run_etl.py
          </p>
        )}
        {backendOnline && ready === true && (
          <p style={{ fontSize: "0.8rem", marginTop: "1rem", color: "#10b981" }}>
            Connected · data ready
          </p>
        )}
      </aside>
      <main className="main">
        {page === "dashboard" && <Dashboard />}
        {page === "live" && <LiveTracker />}
        {page === "rider" && <RiderApp />}
        {page === "map" && <MapExplorer />}
        {page === "od" && <ODMatrix />}
        {page === "traffic" && <Traffic />}
        {page === "assistant" && <Assistant />}
      </main>
    </div>
  );
}
