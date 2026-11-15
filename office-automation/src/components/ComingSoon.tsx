import type { LucideIcon } from 'lucide-react'

/**
 * Page body for modules planned for the next phase.
 * It only lists what will come — no buttons that do nothing.
 */
export function ComingSoon({
  icon: Icon,
  title,
  intro,
  features,
}: {
  icon: LucideIcon
  title: string
  intro: string
  features: string[]
}) {
  return (
    <div className="page">
      <section className="card coming-soon">
        <div className="module-icon large">
          <Icon size={34} aria-hidden />
        </div>
        <div>
          <h2>
            {title} <span className="badge badge-soon">Next phase</span>
          </h2>
          <p className="muted">{intro}</p>
        </div>
      </section>
      <section className="card">
        <h2 className="section-title">Planned features</h2>
        <ul className="feature-list">
          {features.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
        <p className="muted small">
          The foundation (login, roles, security and navigation) is complete. These tools will be added in the next
          development phase.
        </p>
      </section>
    </div>
  )
}
