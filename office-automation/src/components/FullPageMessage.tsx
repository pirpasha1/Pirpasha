import type { ReactNode } from 'react'

/** A centered card used for loading, errors and setup instructions. */
export function FullPageMessage({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="center-page">
      <div className="card center-card">
        <h1 className="center-title">{title}</h1>
        {children}
      </div>
    </div>
  )
}

export function LoadingScreen() {
  return (
    <div className="center-page" role="status" aria-live="polite">
      <div className="spinner" aria-hidden />
      <span className="sr-only">Loading…</span>
    </div>
  )
}
