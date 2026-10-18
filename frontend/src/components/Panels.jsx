const Card = ({ title, right, children, className = '' }) => (
  <section className={`rounded-xl border border-ops-line bg-ops-card p-3 ${className}`}>
    <div className="mb-2 flex items-center justify-between">
      <h3 className="text-sm font-semibold text-sky-300">{title}</h3>
      {right}
    </div>
    {children}
  </section>
)

const prioCls = { high: 'bg-red-500/20 text-red-300', medium: 'bg-amber-500/20 text-amber-300', low: 'bg-green-500/20 text-green-300' }
const Badge = ({ cls, children }) => <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${cls}`}>{children}</span>

export function Reports({ state }) {
  const st = state.report_status || {}
  const parsed = Object.fromEntries((state.parsed || []).map((p) => [p.id, p]))
  return (
    <Card title={`Incoming Reports (${state.raw_reports.length})`} className="max-h-72 overflow-auto">
      {state.raw_reports.length === 0 && <p className="text-xs text-slate-400">Waiting for reports...</p>}
      {state.raw_reports.map((r) => (
        <div key={r.id} className="mb-1 rounded bg-slate-900/60 p-2 text-xs">
          <div className="flex items-center justify-between">
            <b>{r.id} - {r.village}</b>
            <span className="space-x-1">
              {parsed[r.id] && <Badge cls={prioCls[parsed[r.id].urgency >= 4 ? 'high' : parsed[r.id].urgency === 3 ? 'medium' : 'low']}>U{parsed[r.id].urgency}</Badge>}
              {st[r.id] === 'duplicate' && <Badge cls="bg-orange-500/20 text-orange-300">Merged</Badge>}
              {st[r.id] === 'conflict' && <Badge cls="bg-fuchsia-500/20 text-fuchsia-300">Conflict</Badge>}
            </span>
          </div>
          <div className="text-slate-300">{r.text}</div>
          {parsed[r.id] && <div className="text-slate-500">needs: {parsed[r.id].needs.join(', ') || '-'} | people: {parsed[r.id].people} | {parsed[r.id].language}</div>}
        </div>
      ))}
    </Card>
  )
}

export function Verification({ state }) {
  return (
    <Card title="Verification Results">
      {state.verified.length === 0 && <p className="text-xs text-slate-400">Not run yet.</p>}
      {state.merge_log.map((m, i) => <div key={i} className="mb-1 rounded border border-orange-500/30 bg-orange-500/10 p-1.5 text-xs text-orange-200">{m}</div>)}
      <div className="max-h-48 overflow-auto">
        {state.verified.map((v) => (
          <div key={v.id} className="mb-1 flex items-center justify-between rounded bg-slate-900/60 p-1.5 text-xs">
            <span>{v.id} {v.village} <span className="text-slate-500">({v.people} ppl, conf {v.confidence})</span></span>
            <span className="space-x-1">
              <Badge cls={prioCls[v.priority]}>{v.priority}</Badge>
              <Badge cls={v.status === 'valid' ? 'bg-sky-500/20 text-sky-300' : v.status === 'merged' ? 'bg-orange-500/20 text-orange-300' : 'bg-fuchsia-500/20 text-fuchsia-300'}>
                {v.status === 'valid' ? 'Valid' : v.status === 'merged' ? 'Merged' : 'Conflict'}
              </Badge>
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function Resources({ state }) {
  const tot = state.inventory_total
  const left = state.inventory_left
  const rows = [
    ['Food Packets', 'food_packets', tot.food_packets],
    ['Medicines', 'medicines', tot.medicines],
    ['Water Bottles', 'water_bottles', tot.water_bottles],
    ['Volunteers', 'volunteers', tot.volunteers],
  ]
  return (
    <Card title="Available Resources (Limited)">
      {rows.map(([label, key, total]) => {
        const rem = left[key] ?? total
        return (
          <div key={key} className="mb-1.5 text-xs">
            <div className="flex justify-between"><span>{label}</span><span>{rem} / {total}</span></div>
            <div className="h-1.5 rounded bg-slate-800"><div className="h-1.5 rounded bg-sky-400" style={{ width: `${(rem / total) * 100}%` }} /></div>
          </div>
        )
      })}
      <div className="mt-1 text-xs text-slate-300">Boats {tot.boats} | Trucks {tot.trucks} | Helicopters {tot.helicopters}</div>
      {state.plan && Object.keys(state.plan.shortages).length > 0 && (
        <div className="mt-2 rounded bg-red-500/10 p-1.5 text-xs text-red-300">
          Shortages: {Object.entries(state.plan.shortages).map(([k, v]) => `${k} ${v}`).join(', ')}
        </div>
      )}
    </Card>
  )
}

export function Teams({ state }) {
  const items = state.plan?.items || []
  return (
    <Card title={`Response Teams (${state.teams.length})`}>
      {state.teams.map((t) => {
        const jobs = items.filter((i) => i.team === t.name && i.status === 'planned')
        return (
          <div key={t.name} className="mb-1 rounded bg-slate-900/60 p-1.5 text-xs">
            <b>Team {t.name}</b> <span className="text-slate-400">{t.assets.join(' + ')} + {t.volunteers} volunteers</span>
            <div className="text-slate-300">{jobs.length ? jobs.map((j) => `${j.village} (${j.eta_label})`).join(' -> ') : 'idle / support'}</div>
          </div>
        )
      })}
    </Card>
  )
}

export function Feed({ log }) {
  return (
    <Card title="Agent Activity Feed" className="max-h-72 overflow-auto">
      {log.length === 0 && <p className="text-xs text-slate-400">No agent messages yet.</p>}
      {[...log].reverse().map((l) => (
        <div key={l.n} className="mb-1 border-l-2 border-sky-500/60 pl-2 text-[11px]">
          <span className="text-slate-500">{l.ts}</span> <b className="text-sky-300">{l.from}</b> to <b className="text-emerald-300">{l.to}</b>
          <span className="text-slate-500"> [{l.type}]</span>
          <div className="text-slate-300">{l.summary}</div>
        </div>
      ))}
    </Card>
  )
}

export function Conflicts({ state }) {
  if (!state.conflicts.length) return null
  return (
    <Card title="Conflict Detected and Resolution">
      {state.conflicts.map((c) => (
        <div key={c.id} className="mb-1.5 rounded border border-red-500/40 bg-red-500/10 p-1.5 text-xs">
          <div className="font-semibold text-red-300">{c.resource}: {c.winner_village} vs {c.loser_village}</div>
          <div className="mt-1 rounded border border-green-500/40 bg-green-500/10 p-1 text-green-200">Resolution: {c.resolution}</div>
        </div>
      ))}
    </Card>
  )
}

export function Plan({ state, onApprove, onChanges, busy }) {
  const plan = state.plan
  if (!plan) return <Card title="Final Recovery Plan"><p className="text-xs text-slate-400">No plan yet.</p></Card>
  const approved = plan.status === 'approved'
  return (
    <Card title={`Final Recovery Plan v${plan.version}`} right={<Badge cls={approved ? 'bg-green-500/20 text-green-300' : 'bg-amber-500/20 text-amber-300'}>{approved ? 'APPROVED - DISPATCHED' : 'APPROVAL REQUIRED'}</Badge>}>
      <p className="mb-2 text-xs text-slate-300">{plan.explanation}</p>
      {plan.items.map((i) => (
        <div key={i.request_id} className="mb-1 flex items-start justify-between rounded bg-slate-900/60 p-1.5 text-xs">
          <div>
            <span className={i.status === 'planned' ? 'text-green-400' : 'text-amber-400'}>{i.status === 'planned' ? '✔' : '…'}</span>{' '}
            <b>{i.village}</b> <Badge cls={prioCls[i.priority]}>{i.priority}</Badge>
            <div className="text-slate-400">
              {i.status === 'planned' ? `${i.vehicle_id} (${i.mode}) via ${i.path.join(' > ')} | team ${i.team} | ${i.volunteers} volunteers` : i.notes}
            </div>
            {Object.keys(i.shortages).length > 0 && <div className="text-red-300">short: {Object.entries(i.shortages).map(([k, v]) => `${k} ${v}`).join(', ')}</div>}
          </div>
          <div className="text-right"><div className="font-semibold text-sky-300">{i.eta_label}</div>{i.dispatched && <Badge cls="bg-green-500/20 text-green-300">dispatched</Badge>}</div>
        </div>
      ))}
      {!approved && (
        <div className="mt-2 flex gap-2">
          <button disabled={busy} onClick={onApprove} className="flex-1 rounded-lg bg-green-500 py-1.5 text-sm font-bold text-black hover:bg-green-400 disabled:opacity-50">Approve Plan</button>
          <button disabled={busy} onClick={onChanges} className="flex-1 rounded-lg border border-slate-600 py-1.5 text-sm hover:bg-slate-800 disabled:opacity-50">Request Changes (no helicopter)</button>
        </div>
      )}
      <p className="mt-2 text-[11px] text-orange-300">{state.disclaimer}</p>
    </Card>
  )
}

export function Diff({ state }) {
  const changed = (state.diff || []).filter((d) => d.changed)
  if (!state.blocked.length || !changed.length) return null
  return (
    <Card title="Replanned: Before / After" right={<Badge cls="bg-red-500/20 text-red-300">{state.blocked_events.at(-1)}</Badge>}>
      {changed.map((d) => (
        <div key={d.request_id} className="mb-1 grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded bg-slate-900/60 p-1.5 text-xs">
          <div><b>{d.village}</b><div className="text-red-300">{d.before.vehicle} ({d.before.mode}) {d.before.eta}</div></div>
          <span className="text-sky-300">»»</span>
          <div className="text-green-300">{d.after.vehicle} ({d.after.mode}) {d.after.eta}</div>
        </div>
      ))}
    </Card>
  )
}

export function Recomputing({ step }) {
  const steps = ['Checking alternative routes', 'Reallocating vehicles', 'Updating ETA for all locations']
  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60">
      <div className="w-80 rounded-xl border border-sky-500/50 bg-ops-card p-4">
        <div className="mb-3 flex items-center gap-2 font-semibold text-sky-300"><span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />Agents Recomputing...</div>
        {steps.map((s, i) => <div key={s} className={`text-sm ${i < step ? 'text-green-400' : 'text-slate-500'}`}>{i < step ? '✔' : '○'} {s}</div>)}
      </div>
    </div>
  )
}
