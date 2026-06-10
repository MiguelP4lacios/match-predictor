interface ErrorBannerProps {
  onRetry?: () => void
}

export default function ErrorBanner({ onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="rounded border border-red-300 bg-red-50 p-4 text-red-700"
    >
      <p className="font-semibold">API no disponible</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
