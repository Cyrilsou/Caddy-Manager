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
const AuditLogPage = lazy(() => import("@/pages/audit-log"));
const SettingsPage = lazy(() => import("@/pages/settings"));
const CachePage = lazy(() => import("@/pages/cache"));

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Suspense fallback={<PageLoader />}><DashboardPage /></Suspense>} />
          <Route path="/domains" element={<Suspense fallback={<PageLoader />}><DomainsPage /></Suspense>} />
          <Route path="/backends" element={<Suspense fallback={<PageLoader />}><BackendsPage /></Suspense>} />
          <Route path="/config" element={<Suspense fallback={<PageLoader />}><ConfigPage /></Suspense>} />
          <Route path="/certificates" element={<Suspense fallback={<PageLoader />}><CertificatesPage /></Suspense>} />
          <Route path="/cloudflare" element={<Suspense fallback={<PageLoader />}><CloudflarePage /></Suspense>} />
          <Route path="/cache" element={<Suspense fallback={<PageLoader />}><CachePage /></Suspense>} />
          <Route path="/audit" element={<Suspense fallback={<PageLoader />}><AuditLogPage /></Suspense>} />
          <Route path="/settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
