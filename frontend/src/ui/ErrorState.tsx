interface ErrorStateProps {
  onRetry?: () => void
  message?: string
}

export function ErrorState({ onRetry, message = 'API no disponible' }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-danger"
    >
      <p className="font-semibold">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded bg-danger px-3 py-1 text-sm text-white hover:opacity-90"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
