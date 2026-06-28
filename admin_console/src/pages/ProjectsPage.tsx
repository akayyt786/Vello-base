import React, { useEffect, useState } from 'react'
import { api } from '../api'

interface Props { onSelect: (id: string) => void }

export function ProjectsPage({ onSelect }: Props) {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listProjects().then(p => { setProjects(p); setLoading(false) }).catch(() => { setError('Failed to load projects'); setLoading(false) })
  }, [])

  if (loading) return <p style={{ color: '#94a3b8' }}>Loading projects…</p>
  if (error) return <p style={{ color: '#f87171' }}>{error}</p>

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0', marginBottom: 20 }}>Projects</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {projects.map(p => (
          <div key={p.id} onClick={() => onSelect(p.id)} style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10, padding: 20, cursor: 'pointer', transition: 'border-color 0.15s' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#0ea5e9')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#334155')}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#38bdf8', marginBottom: 6 }}>{p.name}</h3>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 10 }}>{p.description || 'No description'}</p>
            <code style={{ fontSize: 11, color: '#475569' }}>{p.id}</code>
          </div>
        ))}
        {projects.length === 0 && <p style={{ color: '#64748b' }}>No projects yet.</p>}
      </div>
    </div>
  )
}
