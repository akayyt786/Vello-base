import React, { useState, useEffect } from 'react'
import { api, setToken, getToken } from './api'
import { LoginPage } from './pages/LoginPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'

type Page = { name: 'login' } | { name: 'projects' } | { name: 'project'; id: string }

export default function App() {
  const [page, setPage] = useState<Page>({ name: getToken() ? 'projects' : 'login' })
  const [user, setUser] = useState<{ email: string } | null>(null)

  useEffect(() => {
    if (getToken()) {
      api.me().then(u => setUser(u)).catch(() => setPage({ name: 'login' }))
    }
  }, [])

  function onLogin(token: string, email: string) {
    setToken(token)
    setUser({ email })
    setPage({ name: 'projects' })
  }

  function onLogout() {
    setToken('')
    setUser(null)
    setPage({ name: 'login' })
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      {user && (
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid #1e293b', background: '#0f172a' }}>
          <span style={{ fontWeight: 700, fontSize: 18, color: '#38bdf8' }}>⚡ OwnFirebase</span>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <span style={{ color: '#94a3b8', fontSize: 14 }}>{user.email}</span>
            {page.name !== 'projects' && (
              <button onClick={() => setPage({ name: 'projects' })} style={btnStyle('#1e293b')}>← Projects</button>
            )}
            <button onClick={onLogout} style={btnStyle('#1e293b')}>Logout</button>
          </div>
        </header>
      )}
      <main style={{ padding: '24px' }}>
        {page.name === 'login' && <LoginPage onLogin={onLogin} />}
        {page.name === 'projects' && <ProjectsPage onSelect={id => setPage({ name: 'project', id })} />}
        {page.name === 'project' && <ProjectDetailPage projectId={page.id} />}
      </main>
    </div>
  )
}

function btnStyle(bg: string) {
  return { background: bg, color: '#e2e8f0', border: '1px solid #334155', borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13 } as React.CSSProperties
}
