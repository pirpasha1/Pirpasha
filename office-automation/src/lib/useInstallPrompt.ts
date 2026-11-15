import { useCallback, useEffect, useState } from 'react'

// The browser event that lets us show our own "Install app" button
// (Chrome / Edge on Android and desktop support it).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

function isRunningAsApp(): boolean {
  return (
    window.matchMedia?.('(display-mode: standalone)').matches ||
    // iOS Safari
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  )
}

// The event can fire before React has started, so we capture it globally.
let deferredPrompt: BeforeInstallPromptEvent | null = null
const listeners = new Set<() => void>()
if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt = e as BeforeInstallPromptEvent
    listeners.forEach((l) => l())
  })
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null
    listeners.forEach((l) => l())
  })
}

/**
 * Tells you whether the app can be installed right now and gives you
 * a function that opens the browser's install dialog.
 */
export function useInstallPrompt() {
  const [, force] = useState(0)
  useEffect(() => {
    const l = () => force((n) => n + 1)
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])

  const install = useCallback(async () => {
    if (!deferredPrompt) return false
    await deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    deferredPrompt = null
    listeners.forEach((l) => l())
    return outcome === 'accepted'
  }, [])

  return {
    canInstall: deferredPrompt !== null,
    isInstalled: isRunningAsApp(),
    install,
  }
}
