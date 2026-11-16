import { Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import AnalyticsPage from "./pages/AnalyticsPage";
import DeviceDetailPage from "./pages/DeviceDetailPage";
import DevicesPage from "./pages/DevicesPage";
import DiagnosticsPage from "./pages/DiagnosticsPage";
import DiscoveryPage from "./pages/DiscoveryPage";
import NotFoundPage from "./pages/NotFoundPage";
import OverviewPage from "./pages/OverviewPage";
import ReportsPage from "./pages/ReportsPage";
import SecurityPage from "./pages/SecurityPage";
import SettingsPage from "./pages/SettingsPage";
import TopologyPage from "./pages/TopologyPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        <Route path="discovery" element={<DiscoveryPage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="devices/:deviceId" element={<DeviceDetailPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="diagnostics" element={<DiagnosticsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="topology" element={<TopologyPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
