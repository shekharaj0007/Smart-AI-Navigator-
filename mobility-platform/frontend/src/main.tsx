import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ShareTrackRoute } from "./pages/ShareTrackPage";
import "./index.css";

const isTrackPage = /^\/track\//i.test(window.location.pathname);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isTrackPage ? <ShareTrackRoute /> : <App />}
  </React.StrictMode>
);
