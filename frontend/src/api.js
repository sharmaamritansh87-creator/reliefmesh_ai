const call = async (path, method = 'GET', body) => {
  const r = await fetch('/api' + path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || r.statusText)
  return data
}

export const api = {
  state: () => call('/state'),
  graph: () => call('/graph'),
  demoStart: () => call('/demo/start', 'POST'),
  demoStep: () => call('/demo/step', 'POST'),
  demoReset: () => call('/demo/reset', 'POST'),
  seed: () => call('/reports/seed', 'POST'),
  block: (village) => call('/events/road-blocked', 'POST', { village }),
  approve: () => call('/plan/approve', 'POST'),
  changes: (note, exclude_vehicles = []) => call('/plan/request-changes', 'POST', { note, exclude_vehicles }),
  addReport: (r) => call('/reports', 'POST', r),
}
