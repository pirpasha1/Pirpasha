import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="page">
      <section className="card">
        <h2>Page not found</h2>
        <p className="muted">The page you are looking for does not exist.</p>
        <Link to="/" className="btn btn-primary">
          Back to dashboard
        </Link>
      </section>
    </div>
  )
}
