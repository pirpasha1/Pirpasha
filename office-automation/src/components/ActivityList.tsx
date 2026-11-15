import { useEffect, useState } from 'react'
import { describeAction, fetchActivity, formatDateTime } from '../lib/activity'
import type { ActivityEntry } from '../lib/types'

/**
 * Shows recent activity. `nameFor` lets admins see who did each action.
 */
export function ActivityList({
  limit = 10,
  nameFor,
}: {
  limit?: number
  nameFor?: (userId: string) => string | undefined
}) {
  const [items, setItems] = useState<ActivityEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    fetchActivity(limit)
      .then((rows) => active && setItems(rows))
      .catch((e: Error) => active && setError(e.message))
    return () => {
      active = false
    }
  }, [limit])

  if (error) return <p className="alert alert-error">Could not load activity: {error}</p>
  if (!items) return <p className="muted">Loading activity…</p>
  if (items.length === 0) return <p className="muted">No activity yet.</p>

  return (
    <ul className="activity-list">
      {items.map((a) => {
        const who = nameFor?.(a.user_id)
        return (
          <li key={a.id}>
            <div>
              <strong>{describeAction(a.action)}</strong>
              {who && <span className="muted"> — {who}</span>}
              {a.details && <div className="muted small">{a.details}</div>}
            </div>
            <time className="muted small" dateTime={a.created_at}>
              {formatDateTime(a.created_at)}
            </time>
          </li>
        )
      })}
    </ul>
  )
}
