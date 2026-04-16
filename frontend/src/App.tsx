import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { Toaster } from "@/components/shared/toaster";
import { PageLoader } from "@/components/shared/loading-spinner";
import LoginPage from "@/pages/login";

const DashboardPage = lazy(() => import("@/pages/dashboard"));
const DomainsPage = lazy(() => import("@/pages/domains"));
const BackendsPage = lazy(() => import("@/pages/backends"));
const ConfigPage = lazy(() => import("@/pages/config"));
const CertificatesPage = lazy(() => import("@/pages/certificates"));
const CloudflarePage = lazy(() => import("@/pages/cloudflare"));
const CachePage = lazy(() => import("@/pages/cache"));
const DnsCheckPage = lazy(() => import("@/pages/dns-check"));
const LogsPage = lazy(() => import("@/pages/logs"));
const UsersPage = lazy(() => import("@/pages/users"));
const DockerPage = lazy(() => import("@/pages/docker"));
const AuditLogPage = lazy(() => import("@/pages/audit-log"));
const SettingsPage = lazy(() => import("@/pages/settings"));

const S = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<PageLoader />}>{children}</Suspense>
);

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<S><DashboardPage /></S>} />
          <Route path="/domains" element={<S><DomainsPage /></S>} />
          <Route path="/backends" element={<S><BackendsPage /></S>} />
          <Route path="/config" element={<S><ConfigPage /></S>} />
          <Route path="/certificates" element={<S><CertificatesPage /></S>} />
          <Route path="/cloudflare" element={<S><CloudflarePage /></S>} />
          <Route path="/cache" element={<S><CachePage /></S>} />
          <Route path="/dns-check" element={<S><DnsCheckPage /></S>} />
          <Route path="/logs" element={<S><LogsPage /></S>} />
          <Route path="/users" element={<S><UsersPage /></S>} />
          <Route path="/docker" element={<S><DockerPage /></S>} />
          <Route path="/audit" element={<S><AuditLogPage /></S>} />
          <Route path="/settings" element={<S><SettingsPage /></S>} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
