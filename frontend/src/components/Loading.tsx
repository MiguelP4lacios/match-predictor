export default function Loading() {
  return (
    <div aria-label="Cargando" className="space-y-3 p-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-6 animate-pulse rounded bg-gray-200"
        />
      ))}
    </div>
  )
}
