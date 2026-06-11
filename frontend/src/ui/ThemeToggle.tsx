import { useTheme } from '../context/ThemeContext'
import type { ThemePref } from '../context/ThemeContext'

const CYCLE: ThemePref[] = ['system', 'light', 'dark']

const ICONS: Record<ThemePref, string> = {
  system: '💻',
  light: '☀️',
  dark: '🌙',
}

const LABELS: Record<ThemePref, string> = {
  system: 'Sistema',
  light: 'Claro',
  dark: 'Oscuro',
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  function cycleTheme() {
    const idx = CYCLE.indexOf(theme)
    const next = CYCLE[(idx + 1) % CYCLE.length]
    setTheme(next)
  }

  return (
    <button
      onClick={cycleTheme}
      title={`Tema actual: ${LABELS[theme]}`}
      aria-label={`Cambiar tema (actual: ${LABELS[theme]})`}
      className="flex h-8 w-8 items-center justify-center rounded-full text-base transition-colors hover:bg-border/30"
    >
      {ICONS[theme]}
    </button>
  )
}
