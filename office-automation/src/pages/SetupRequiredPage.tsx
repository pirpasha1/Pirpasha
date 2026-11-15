import { FullPageMessage } from '../components/FullPageMessage'

/** Shown when the Supabase settings have not been added to the .env file yet. */
export function SetupRequiredPage() {
  return (
    <FullPageMessage title="Setup required">
      <p className="muted">The app is not connected to Supabase yet. To finish setup:</p>
      <ol className="help-list numbered">
        <li>
          Copy the file <code>.env.example</code> and name the copy <code>.env</code>.
        </li>
        <li>
          In Supabase open <em>Project Settings → API</em> and copy the <strong>Project URL</strong> and the{' '}
          <strong>anon / publishable key</strong> into <code>.env</code>.
        </li>
        <li>
          Stop and restart the app (<code>npm run dev</code>).
        </li>
      </ol>
      <p className="muted small">Full step-by-step instructions are in README.md.</p>
    </FullPageMessage>
  )
}
