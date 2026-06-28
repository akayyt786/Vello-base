import React, { useEffect, useState } from 'react'
import { api } from '../api'

interface Props { projectId: string }

export function ProjectDetailPage({ projectId }: Props) {
  const [project, setProject] = useState<any>(null)
  const [members, setMembers] = useState<any[]>([])
  const [collections, setCollections] = useState<any[]>([])
  const [aiUsage, setAiUsage] = useState<any[]>([])
  const [experiments, setExperiments] = useState<any[]>([])
  const [functions, setFunctions] = useState<any[]>([])
  const [tab, setTab] = useState<'overview'|'members'|'data'|'ai'|'experiments'|'functions'>('overview')

  useEffect(() => {
    api.getProject(projectId).then(setProject)
    api.listMembers(projectId).then(setMembers).catch(() => {})
    api.listCollections(projectId).then(setCollections).catch(() => {})
    api.aiUsage(projectId).then(setAiUsage).catch(() => {})
    api.listExperiments(projectId).then(setExperiments).catch(() => {})
    api.listFunctions(projectId).then(setFunctions).catch(() => {})
  }, [projectId])

  if (!project) return <p style={{ color: '#94a3b8' }}>Loading…</p>

  const tabs = ['overview','members','data','ai','experiments','functions'] as const
  const totalTokens = aiUsage.reduce((s, l) => s + (l.total_tokens || 0), 0)

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{project.name}</h2>
        <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>{project.description}</p>
      </div>
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid #1e293b', paddingBottom: 8 }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: '6px 16px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: tab === t ? 600 : 400, background: tab === t ? '#0ea5e9' : 'transparent', color: tab === t ? '#fff' : '#64748b' }}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
          {[
            { label: 'Members', value: members.length },
            { label: 'Collections', value: collections.length },
            { label: 'AI Requests', value: aiUsage.length },
            { label: 'Tokens Used', value: totalTokens.toLocaleString() },
            { label: 'Experiments', value: experiments.length },
            { label: 'Functions', value: functions.length },
          ].map(stat => (
            <div key={stat.label} style={{ background: '#1e293b', borderRadius: 10, padding: 20, border: '1px solid #334155' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#38bdf8' }}>{stat.value}</div>
              <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'members' && <Table data={members} cols={['user','role','joined_at']} />}
      {tab === 'data' && <Table data={collections} cols={['name','id']} />}
      {tab === 'ai' && <Table data={aiUsage.slice(0,20)} cols={['provider','model','total_tokens','latency_ms','status','created_at']} />}
      {tab === 'experiments' && <Table data={experiments} cols={['name','status','created_at']} />}
      {tab === 'functions' && <Table data={functions} cols={['name','runtime','is_active']} />}
    </div>
  )
}

function Table({ data, cols }: { data: any[]; cols: string[] }) {
  if (!data.length) return <p style={{ color: '#64748b' }}>No data.</p>
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>{cols.map(c => <th key={c} style={{ textAlign: 'left', padding: '8px 12px', color: '#94a3b8', borderBottom: '1px solid #1e293b', fontWeight: 600 }}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #0f172a' }}>
              {cols.map(c => <td key={c} style={{ padding: '8px 12px', color: '#e2e8f0' }}>{String(row[c] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
