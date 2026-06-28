import React, { useState } from 'react'
import { api } from '../api'

interface Props { onLogin: (token: string, email: string) => void }

export function LoginPage({ onLogin }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const { access } = await api.login(email, password)
      onLogin(access, email)
    } catch (err: any) {
      setError(err?.detail?.detail || 'Login failed. Check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 32, width: 360 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#38bdf8', marginBottom: 8 }}>⚡ OwnFirebase</h1>
        <p style={{ color: '#64748b', fontSize: 14, marginBottom: 24 }}>Admin Console</p>
        {error && <div style={{ color: '#f87171', background: '#1f1212', border: '1px solid #dc2626', borderRadius: 6, padding: '8px 12px', marginBottom: 16, fontSize: 14 }}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>Email</label>
          <input style={inputStyle} type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="admin@example.com" />
          <label style={labelStyle}>Password</label>
          <input style={inputStyle} type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" />
          <button type="submit" disabled={loading} style={{ width: '100%', padding: '10px', background: loading ? '#334155' : '#0ea5e9', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 15, marginTop: 8 }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, color: '#94a3b8', marginBottom: 4, marginTop: 12 }
const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 12px', background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', fontSize: 14 }
