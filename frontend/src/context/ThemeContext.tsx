/**
 * ThemeContext — gestión de tema light/dark/system.
 * Persiste en localStorage. Aplica clase "dark" a <html>.
 * El script inline en index.html evita el flash en carga.
 */

import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

export type ThemePref = 'light' | 'dark' | 'system'

interface ThemeContextValue {
  theme: ThemePref
  resolved: 'light' | 'dark'
  setTheme: (t: ThemePref) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const STORAGE_KEY = 'theme'

function resolveTheme(pref: ThemePref): 'light' | 'dark' {
  if (pref === 'light') return 'light'
  if (pref === 'dark') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(resolved: 'light' | 'dark'): void {
  if (resolved === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

function loadPreference(): ThemePref {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return 'system'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemePref] = useState<ThemePref>(loadPreference)

  const resolved = resolveTheme(theme)

  useEffect(() => {
    applyTheme(resolved)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme, resolved])

  function setTheme(t: ThemePref) {
    setThemePref(t)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme debe usarse dentro de ThemeProvider')
  return ctx
}
