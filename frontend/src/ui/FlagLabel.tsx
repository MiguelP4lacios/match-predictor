import { nameToFlag } from '../lib/flags'

type FlagLabelSize = 'sm' | 'md' | 'lg'

const SIZE_CLASSES: Record<FlagLabelSize, string> = {
  sm: 'text-sm gap-1',
  md: 'text-base gap-1.5',
  lg: 'text-lg gap-2',
}

interface FlagLabelProps {
  team: string
  size?: FlagLabelSize
  className?: string
}

export function FlagLabel({ team, size = 'md', className = '' }: FlagLabelProps) {
  const flag = nameToFlag(team)
  return (
    <span className={`inline-flex items-center font-medium ${SIZE_CLASSES[size]} ${className}`}>
      <span aria-hidden="true">{flag}</span>
      <span>{team}</span>
    </span>
  )
}
