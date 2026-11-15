import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { isSupabaseConfigured } from './lib/supabase'
import { AuthProvider } from './context/AuthProvider'
import { AppLayout } from './components/AppLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { DashboardPage } from './pages/DashboardPage'
import { ExcelToolsPage } from './pages/ExcelToolsPage'
import { PdfToolsPage } from './pages/PdfToolsPage'
import { ReportsPage } from './pages/ReportsPage'
import { UsersPage } from './pages/UsersPage'
import { SettingsPage } from './pages/SettingsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SetupRequiredPage } from './pages/SetupRequiredPage'

/**
 * All the screens of the app and who may open them.
 *   /login, /reset-password  -> anyone
 *   everything else          -> logged-in users
 *   /users                   -> administrators only
 */
export default function App() {
  if (!isSupabaseConfigured) return <SetupRequiredPage />

  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="excel" element={<ExcelToolsPage />} />
              <Route path="pdf" element={<PdfToolsPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route element={<ProtectedRoute roles={['admin']} />}>
                <Route path="users" element={<UsersPage />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
