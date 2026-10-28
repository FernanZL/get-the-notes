import type { ReactNode } from 'react'

export function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect x="1" y="4" width="26" height="20" rx="4" fill="none" stroke="#E8EAED" strokeWidth="2" />
      <line x1="10" y1="4" x2="10" y2="24" stroke="#E8EAED" strokeWidth="2" />
      <line x1="18" y1="4" x2="18" y2="24" stroke="#E8EAED" strokeWidth="2" />
      <rect x="7" y="4" width="5" height="11" fill="#1FB5A3" />
      <rect x="16" y="4" width="5" height="11" fill="#FFB547" />
    </svg>
  )
}

export function Header({ children }: { children?: ReactNode }) {
  return (
    <header className="header">
      <a href="#/" className="brand">
        <Logo />
        Get the Notes
      </a>
      {children}
    </header>
  )
}
