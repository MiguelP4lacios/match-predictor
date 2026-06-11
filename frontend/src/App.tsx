import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SignalsPage from './pages/SignalsPage'
import GroupsPage from './pages/GroupsPage'
import GroupDetailPage from './pages/GroupDetailPage'
import MatchesPage from './pages/MatchesPage'
import ModelPage from './pages/ModelPage'
import BetsPage from './pages/BetsPage'
import EstadoPage from './pages/EstadoPage'
import FuturesDashboard from './pages/FuturesDashboard'
import NotFound from './pages/NotFound'
import { CuponProvider } from './context/CuponContext'
import { ThemeProvider } from './context/ThemeContext'
import CuponDrawer from './components/CuponDrawer'
import { AppShell } from './ui/AppShell'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
    },
  },
})

/**
 * AppRoutes — rutas dentro del AppShell, sin BrowserRouter.
 * Exportado por separado para poder testear con MemoryRouter.
 */
export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<SignalsPage />} />
        <Route path="/grupos" element={<GroupsPage />} />
        <Route path="/grupos/:letra" element={<GroupDetailPage />} />
        <Route path="/partidos" element={<MatchesPage />} />
        <Route path="/modelo" element={<ModelPage />} />
        <Route path="/apuestas" element={<BetsPage />} />
        <Route path="/estado" element={<EstadoPage />} />
        <Route path="/futures" element={<FuturesDashboard />} />
        {/* Redirect de /paper → /apuestas para retrocompatibilidad */}
        <Route path="/paper" element={<Navigate to="/apuestas" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <CuponProvider>
            <AppRoutes />
            <CuponDrawer />
          </CuponProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
