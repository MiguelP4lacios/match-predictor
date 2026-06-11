import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { StatusBadge } from './StatusBadge'
import { ThemeToggle } from './ThemeToggle'

interface RouteConfig {
  to: string
  label: string
  end?: boolean
}

export const APP_ROUTES: RouteConfig[] = [
  { to: '/', label: 'Señales', end: true },
  { to: '/grupos', label: 'Grupos' },
  { to: '/partidos', label: 'Partidos' },
  { to: '/modelo', label: 'Modelo' },
  { to: '/apuestas', label: 'Apuestas' },
  { to: '/estado', label: 'Estado' },
]

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive
    ? 'font-semibold text-primary'
    : 'text-text-muted hover:text-text transition-colors'
}

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-bg">
      {/* Header — visible en todos los breakpoints */}
      <header className="border-b border-border bg-surface shadow-sm">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          {/* Wordmark */}
          <span className="mr-auto font-bold text-text">🏆 WC26</span>

          {/* Top nav — visible ≥md */}
          <nav
            data-testid="nav-top"
            className="hidden items-center gap-5 md:flex"
          >
            {APP_ROUTES.map(({ to, label, end }) => (
              <NavLink key={to} to={to} end={end} className={navLinkClass}>
                <span className="text-sm">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Estado del sistema + cambio de tema */}
          <div className="flex items-center gap-2">
            <StatusBadge />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content — con padding-bottom en móvil para bottom-bar */}
      <main className="mx-auto max-w-5xl px-4 py-6 pb-24 md:pb-6">
        {children}
      </main>

      {/* Bottom tab bar — visible <md (z-30, debajo del FAB del cupón z-40) */}
      <nav
        data-testid="nav-bottom"
        className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-border bg-surface md:hidden"
      >
        {APP_ROUTES.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center justify-center py-2 text-xs transition-colors ${
                isActive ? 'text-primary font-semibold' : 'text-text-muted'
              }`
            }
          >
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
