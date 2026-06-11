interface Tab {
  id: string
  label: string
}

interface TabsProps {
  tabs: Tab[]
  value: string
  onChange: (id: string) => void
  className?: string
}

export function Tabs({ tabs, value, onChange, className = '' }: TabsProps) {
  return (
    <div
      role="tablist"
      className={`flex gap-1 rounded-lg border border-border bg-surface p-1 ${className}`}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={tab.id === value}
          onClick={() => onChange(tab.id)}
          className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
            tab.id === value
              ? 'bg-primary text-primary-fg shadow-sm'
              : 'text-text-muted hover:text-text'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
