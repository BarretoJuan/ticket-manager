import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { ToastViewport } from './components/ui/ToastViewport'
import { LoginPage } from './pages/LoginPage'
import { AdminEventsPage } from './pages/AdminEventsPage'
import { SatAutomationPage } from './pages/SatAutomationPage'
import { UserEventsPage } from './pages/UserEventsPage'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Authenticated area (any role); role-specific routes nested inside */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route element={<ProtectedRoute role="USER" />}>
              <Route path="/" element={<UserEventsPage />} />
            </Route>
            <Route element={<ProtectedRoute role="ADMIN" />}>
              <Route path="/admin" element={<AdminEventsPage />} />
              <Route path="/admin/sat" element={<SatAutomationPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <ToastViewport />
    </>
  )
}
