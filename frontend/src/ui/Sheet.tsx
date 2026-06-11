import { useEffect } from 'react'
import type { ReactNode } from 'react'

interface SheetProps {
  open: boolean
  onClose: () => void
  title?: string
  side?: 'left' | 'right' | 'bottom'
  footer?: ReactNode
  children: ReactNode
}

export function Sheet({ open, onClose, title, side = 'right', footer, children }: SheetProps) {
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  const PANEL_CLASSES: Record<NonNullable<SheetProps['side']>, string> = {
    right: 'right-0 top-0 h-full w-80 max-w-full',
    left: 'left-0 top-0 h-full w-80 max-w-full',
    bottom: 'bottom-0 left-0 w-full rounded-t-2xl',
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        data-testid="sheet-backdrop"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`absolute flex flex-col bg-surface shadow-xl ${PANEL_CLASSES[side]}`}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-base font-semibold text-text">{title}</h2>
            <button
              onClick={onClose}
              aria-label="Cerrar"
              className="rounded p-1 text-text-muted hover:text-text"
            >
              ✕
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        {footer && (
          <div className="border-t border-border p-4">{footer}</div>
        )}
      </div>
    </div>
  )
}
