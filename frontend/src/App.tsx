import { Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { TopBar } from "./components/TopBar";
import { Footer } from "./components/Disclaimer";
import { Banner } from "./components/Banner";
import { RequireAuth } from "./components/RouteGuards";
import { useSyncExternalStore } from "react";
import { USE_MOCKS, offlineStore } from "./api/client";
import { LoginPage } from "./pages/LoginPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { SitePage } from "./pages/SitePage";
import { IncidentPage } from "./pages/IncidentPage";
import { AlertsPage } from "./pages/AlertsPage";
import { HistoryPage } from "./pages/HistoryPage";
import { AssetsPage } from "./pages/AssetsPage";
import { RulesPage } from "./pages/RulesPage";
import { SystemPage } from "./pages/SystemPage";
import { FieldPage } from "./pages/FieldPage";
import { HandoffPage } from "./pages/HandoffPage";

function Layout() {
  const loc = useLocation();
  const offline = useSyncExternalStore(offlineStore.subscribe, offlineStore.get);
  return (
    <div className="app-shell">
      <div className="no-print"><TopBar /></div>
      <Banner show={USE_MOCKS} tone="info">Mock mode — interactive demo data. Every screen runs without a backend.</Banner>
      <Banner show={!USE_MOCKS && offline} tone="warn">Engine offline — showing built-in demo data until it is reachable again.</Banner>
      <AnimatePresence mode="wait">
        <motion.main key={loc.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }} style={{ flex: 1 }}>
          <Outlet />
        </motion.main>
      </AnimatePresence>
      <div className="no-print"><Footer /></div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route element={<RequireAuth />}>
          <Route path="/" element={<PortfolioPage />} />
          <Route path="/sites/:siteId" element={<SitePage />} />
          <Route path="/sites/:siteId/handoff" element={<HandoffPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/field/:siteId" element={<FieldPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
