import type { ReactNode } from 'react'

export type BadgeVariant = 'neutral' | 'success' | 'warn' | 'danger'

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  neutral: 'bg-border text-text-muted',
  success: 'bg-success/15 text-success',
  warn: 'bg-warn/15 text-warn',
  danger: 'bg-danger/15 text-danger',
}

interface BadgeProps {
  variant: BadgeVariant
  className?: string
  children: ReactNode
}

export function Badge({ variant, className = '', children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
