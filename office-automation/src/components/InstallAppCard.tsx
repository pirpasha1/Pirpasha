import { Download, MonitorSmartphone } from 'lucide-react'
import { useInstallPrompt } from '../lib/useInstallPrompt'

/**
 * Explains how to install the app. When the browser allows it, shows a real
 * "Install app" button; otherwise shows short manual instructions instead
 * (so there is never a button that does nothing).
 */
export function InstallAppCard() {
  const { canInstall, isInstalled, install } = useInstallPrompt()

  return (
    <section className="card">
      <div className="card-header">
        <MonitorSmartphone aria-hidden size={20} />
        <h2>Install the app</h2>
      </div>
      {isInstalled ? (
        <p className="muted">The app is installed and running as an app on this device. ✔</p>
      ) : canInstall ? (
        <>
          <p className="muted">
            Add Office Automation to your home screen or desktop for quick access, like a normal app.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => void install()}>
            <Download size={18} aria-hidden /> Install app
          </button>
        </>
      ) : (
        <ul className="help-list">
          <li>
            <strong>Android (Chrome):</strong> tap the ⋮ menu → <em>Add to Home screen</em> / <em>Install app</em>.
          </li>
          <li>
            <strong>Desktop (Chrome / Edge):</strong> click the install icon at the right end of the address bar.
          </li>
          <li>
            <strong>iPhone (Safari):</strong> tap Share → <em>Add to Home Screen</em>.
          </li>
        </ul>
      )}
    </section>
  )
}
