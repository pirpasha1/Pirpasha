import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LogOut, Menu, X } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { MODULES, modulesForRole } from '../config/modules'
import { RoleBadge } from './RoleBadge'

/**
 * The main frame of the app: a side menu (a slide-out drawer on phones),
 * a top bar with the page title, and the current page in the middle.
 */
export function AppLayout() {
  const { profile, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  const location = useLocation()

  if (!profile) return null
  const modules = modulesForRole(profile.role)
  const current =
    MODULES.find((m) => m.path !== '/' && location.pathname.startsWith(m.path)) ?? MODULES[0]

  async function handleSignOut() {
    setSigningOut(true)
    try {
      await signOut()
    } finally {
      setSigningOut(false)
    }
  }

  const displayName = profile.full_name || profile.email

  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>

      <aside className={`sidebar ${menuOpen ? 'open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-brand">
          <img src="/favicon.svg" alt="" width={32} height={32} />
          <span>Office Automation</span>
          <button
            type="button"
            className="icon-btn sidebar-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            <X size={22} />
          </button>
        </div>

        <nav className="nav">
          {modules.map((m) => (
            <NavLink
              key={m.path}
              to={m.path}
              end={m.path === '/'}
              className="nav-link"
              onClick={() => setMenuOpen(false)} // close the phone menu after choosing a page
            >
              <m.icon size={20} aria-hidden />
              <span>{m.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="avatar" aria-hidden>
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="user-chip-text">
              <span className="user-name" title={displayName}>
                {displayName}
              </span>
              <RoleBadge role={profile.role} />
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            onClick={() => void handleSignOut()}
            disabled={signingOut}
          >
            <LogOut size={18} aria-hidden /> {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      </aside>

      {menuOpen && <div className="backdrop" onClick={() => setMenuOpen(false)} aria-hidden />}

      <div className="main-area">
        <header className="topbar">
          <button
            type="button"
            className="icon-btn menu-btn"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            aria-expanded={menuOpen}
          >
            <Menu size={24} />
          </button>
          <h1 className="topbar-title">{current.label}</h1>
        </header>
        <main id="main" className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
