import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api";

interface Message {
  role: "user" | "assistant";
  text: string;
  chart?: { type: string; data: unknown };
}

const SUGGESTIONS = [
  "Give me a dataset overview",
  "Which transport mode is most common?",
  "Show peak traffic hours",
  "What are the top OD flows?",
  "Show heatmap hotspots",
  "What is the ML model accuracy?",
  "User 010 stats",
];

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async (question: string) => {
    if (!question.trim()) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(question);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: res.answer, chart: res.chart },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${e}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h2 className="page-title">AI Mobility Assistant</h2>
      <p className="page-sub">Ask questions about transport modes, traffic, OD flows, and users</p>

      <div className="panel">
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" onClick={() => send(s)} style={{ fontSize: "0.8rem" }}>
              {s}
            </button>
          ))}
        </div>

        <div className="chat-box">
          {messages.map((m, i) => (
            <div key={i}>
              <div className={`chat-msg ${m.role}`}>{m.text}</div>
              {m.chart?.type === "bar" && m.chart.data && (
                <ChartBar data={m.chart.data as Record<string, number>} />
              )}
              {m.chart?.type === "line" && m.chart.data && (
                <ChartLine data={m.chart.data as Record<string, number>} />
              )}
            </div>
          ))}
          {loading && <div className="chat-msg">Thinking...</div>}
        </div>

        <div className="chat-input-row" style={{ marginTop: "1rem" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ask about mobility data..."
          />
          <button type="button" onClick={() => send(input)} disabled={loading}>
            Send
          </button>
        </div>
      </div>
    </>
  );
}

function ChartBar({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <XAxis dataKey="name" stroke="#8b9cb3" />
        <YAxis stroke="#8b9cb3" />
        <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
        <Bar dataKey="value" fill="#10b981" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ChartLine({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data)
    .map(([hour, count]) => ({ hour: `${hour}:00`, count }))
    .sort((a, b) => parseInt(a.hour) - parseInt(b.hour));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <XAxis dataKey="hour" stroke="#8b9cb3" />
        <YAxis stroke="#8b9cb3" />
        <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2d3a4f" }} />
        <Bar dataKey="count" fill="#3b82f6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
