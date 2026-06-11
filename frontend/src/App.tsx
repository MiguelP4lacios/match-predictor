import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SignalsPage from './pages/SignalsPage'
import GroupsPage from './pages/GroupsPage'
import GroupDetailPage from './pages/GroupDetailPage'
import MatchesPage from './pages/MatchesPage'
import ModelPage from './pages/ModelPage'
import BetsPage from './pages/BetsPage'
import NotFound from './pages/NotFound'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
    },
  },
})

const NAV_LINKS = [
  { to: '/', label: 'Señales', end: true },
  { to: '/grupos', label: 'Grupos' },
  { to: '/partidos', label: 'Partidos' },
  { to: '/modelo', label: 'Modelo' },
  { to: '/apuestas', label: 'Apuestas' },
]

/**
 * AppRoutes — rutas + navegación, sin BrowserRouter.
 * Exportado por separado para poder testear con MemoryRouter.
 */
export function AppRoutes() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <nav className="mx-auto flex max-w-5xl gap-6 px-4 py-3">
          <span className="mr-auto font-bold text-gray-800">🏆 WC 2026</span>
          {NAV_LINKS.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${
                  isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<SignalsPage />} />
          <Route path="/grupos" element={<GroupsPage />} />
          <Route path="/grupos/:letra" element={<GroupDetailPage />} />
          <Route path="/partidos" element={<MatchesPage />} />
          <Route path="/modelo" element={<ModelPage />} />
          <Route path="/apuestas" element={<BetsPage />} />
          {/* Redirect de /paper → /apuestas para retrocompatibilidad */}
          <Route path="/paper" element={<Navigate to="/apuestas" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
