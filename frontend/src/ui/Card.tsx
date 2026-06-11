import type { ReactNode } from 'react'

interface CardProps {
  title?: ReactNode
  footer?: ReactNode
  className?: string
  children: ReactNode
}

export function Card({ title, footer, className = '', children }: CardProps) {
  return (
    <div className={`rounded-lg border border-border bg-surface p-4 shadow-sm ${className}`}>
      {title && (
        <div className="mb-3 border-b border-border pb-2 text-sm font-semibold text-text">
          {title}
        </div>
      )}
      <div className="text-text">{children}</div>
      {footer && (
        <div className="mt-3 border-t border-border pt-2 text-xs text-text-muted">{footer}</div>
      )}
    </div>
  )
}
