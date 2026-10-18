import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import MapView from './components/MapView'
import { Conflicts, Diff, Feed, Plan, Recomputing, Reports, Resources, Teams, Verification } from './components/Panels'

const STEPS = ['Alert', 'Reports', 'Verify', 'Resources', 'Routing', 'Conflict', 'Road blocked', 'Approve']

export default function App() {
  const [state, setState] = useState(null)
  const [graph, setGraph] = useState(null)
  const [busy, setBusy] = useState(false)
  const [recompute, setRecompute] = useState(0)
  const [error, setError] = useState('')

  const refresh = useCallback(() => api.state().then(setState).catch(() => setError('Backend not reachable on :8080 - run `python -m backend.run_all`')), [])

  useEffect(() => {
    api.graph().then(setGraph).catch(() => {})
    refresh()
    const t = setInterval(refresh, 1500)
    return () => clearInterval(t)
  }, [refresh])

  const run = async (fn) => {
    setBusy(true); setError('')
    try { await fn() } catch (e) { setError(e.message) }
    await refresh(); setBusy(false)
  }

  const simulateBlock = () => run(async () => {
    if (!state?.plan) await api.seed()
    setRecompute(1)
    const t1 = setTimeout(() => setRecompute(2), 700)
    const t2 = setTimeout(() => setRecompute(3), 1400)
    await api.block('Dhemaji')
    await new Promise((r) => setTimeout(r, 2000))
    clearTimeout(t1); clearTimeout(t2); setRecompute(0)
  })

  if (!state) return <div className="p-6 text-slate-300">{error || 'Connecting...'}</div>

  return (
    <div className="min-h-screen p-3">
      <div className="mb-2 rounded bg-red-600 py-1 text-center text-xs font-bold tracking-wide text-white">{state.banner}</div>
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-extrabold text-white">ReliefMesh <span className="text-sky-400">AI</span></h1>
          <p className="text-xs text-slate-400">Multi-Agent Disaster Response - North East India | Crisis reports se coordinated action tak</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button disabled={busy} onClick={() => run(api.demoStart)} className="rounded-lg bg-sky-500 px-3 py-1.5 text-sm font-bold text-black disabled:opacity-50">Start Demo</button>
          <button disabled={busy || state.demo_step < 0 || state.demo_step >= 7} onClick={() => run(api.demoStep)} className="rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-bold text-black disabled:opacity-40">Next Step »</button>
          <button disabled={busy} onClick={simulateBlock} className="rounded-lg bg-red-500 px-3 py-1.5 text-sm font-bold text-white disabled:opacity-50">Simulate Road Blocked</button>
          <button disabled={busy} onClick={() => run(api.seed)} className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm">Load All Reports</button>
          <button disabled={busy} onClick={() => run(api.demoReset)} className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm">Reset</button>
        </div>
      </header>

      <div className="mb-3 flex flex-wrap gap-1 text-[11px]">
        {STEPS.map((s, i) => (
          <span key={s} className={`rounded-full px-2 py-0.5 ${i <= state.demo_step ? 'bg-sky-500 text-black' : 'bg-slate-800 text-slate-400'}`}>{i + 1}. {s}</span>
        ))}
      </div>
      {state.alert && <div className="mb-3 rounded border border-amber-500/50 bg-amber-500/10 p-2 text-sm text-amber-200">{state.alert}</div>}
      {error && <div className="mb-3 rounded border border-red-500/50 bg-red-500/10 p-2 text-sm text-red-300">{error}</div>}

      <div className="grid gap-3 lg:grid-cols-[1fr_1.3fr_1fr]">
        <div className="space-y-3"><Reports state={state} /><Verification state={state} /></div>
        <div className="space-y-3">
          <div className="rounded-xl border border-ops-line bg-ops-card p-2"><MapView graph={graph} state={state} /></div>
          <Diff state={state} />
          <Plan state={state} busy={busy} onApprove={() => run(api.approve)} onChanges={() => run(() => api.changes('Operator: avoid helicopter', ['Heli-1']))} />
        </div>
        <div className="space-y-3"><Resources state={state} /><Teams state={state} /><Conflicts state={state} /><Feed log={state.agent_log} /></div>
      </div>
      {recompute > 0 && <Recomputing step={recompute} />}
    </div>
  )
}
