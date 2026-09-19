import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";
import App from "./App";
import { BRAND } from "./brand";

document.title = `${BRAND.name} — ${BRAND.tagline}`;
import { AuthProvider } from "./state/AuthContext";
import { TimeProvider } from "./state/TimeContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TimeProvider>
          <App />
        </TimeProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
