import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const PRIO = { high: '#ef4444', medium: '#f59e0b', low: '#22c55e' }

export default function MapView({ graph, state }) {
  const el = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    if (map.current || !el.current) return
    map.current = L.map(el.current, { center: [26.6, 93.0], zoom: 6, zoomControl: true })
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap', maxZoom: 12,
    })
    tiles.on('tileerror', () => setOffline(true))
    tiles.addTo(map.current)
    layer.current = L.layerGroup().addTo(map.current)
  }, [])

  useEffect(() => {
    if (!graph || !layer.current) return
    const g = layer.current
    g.clearLayers()
    const pos = Object.fromEntries(graph.nodes.map((n) => [n.id, [n.lat, n.lon]]))
    const prio = Object.fromEntries((state?.verified || []).map((r) => [r.village, r.priority]))
    const blocked = new Set(state?.blocked || [])

    // faint network (offline-safe: drawn without tiles)
    graph.edges.forEach((e) => {
      const isBlocked = blocked.has(e.id)
      L.polyline([pos[e.a], pos[e.b]], isBlocked
        ? { color: '#ef4444', weight: 3, dashArray: '8 6' }
        : { color: e.mode === 'river' ? '#1d4ed8' : '#334155', weight: 1.5, opacity: 0.6, dashArray: e.mode === 'river' ? '2 6' : null }
      ).addTo(g)
    })

    // plan routes: best = green, alternate = yellow dashed
    ;(state?.plan?.items || []).forEach((it) => {
      if (it.alt?.path?.length > 1) {
        L.polyline(it.alt.path.map((p) => pos[p]), { color: '#facc15', weight: 2, dashArray: '4 8', opacity: 0.8 })
          .bindTooltip(`Alt: ${it.alt.vehicle_id} ETA ${it.alt.eta_h}h`).addTo(g)
      }
    })
    ;(state?.plan?.items || []).forEach((it) => {
      if (it.path?.length > 1) {
        L.polyline(it.path.map((p) => pos[p]), {
          color: '#22c55e', weight: 4, opacity: 0.95, dashArray: it.mode === 'air' ? '1 9' : it.mode === 'river' ? '10 5' : null,
        }).bindTooltip(`${it.village}: ${it.vehicle_id} (${it.mode}) ETA ${it.eta_label}`).addTo(g)
      }
    })

    graph.nodes.forEach((n) => {
      if (n.kind === 'base') {
        L.marker(pos[n.id], { icon: L.divIcon({ className: '', html: `<div style="background:#38bdf8;color:#04121f;font:700 10px sans-serif;padding:2px 6px;border-radius:6px;white-space:nowrap">⌂ ${n.id}</div>` }) }).addTo(g)
      } else {
        const p = prio[n.id]
        L.circleMarker(pos[n.id], { radius: p ? 9 : 6, color: '#0b1220', weight: 2, fillColor: PRIO[p] || '#64748b', fillOpacity: 1 })
          .bindTooltip(`${n.id}${p ? ' - ' + p + ' priority' : ''}`, { permanent: !!p, direction: 'right', className: '' }).addTo(g)
      }
    })
  }, [graph, state])

  return (
    <div className="relative">
      <div ref={el} style={{ height: 420 }} />
      {offline && (
        <div className="absolute bottom-2 left-2 z-[500] rounded bg-amber-500/90 px-2 py-1 text-xs font-semibold text-black">
          Offline mode: map tiles unavailable, network still drawn
        </div>
      )}
      <div className="absolute right-2 top-2 z-[500] space-y-1 rounded-lg bg-black/60 p-2 text-[11px]">
        <div><span className="text-green-400">━━</span> Best route</div>
        <div><span className="text-yellow-300">┅┅</span> Alternate</div>
        <div><span className="text-red-400">╌╌</span> Blocked</div>
        <div><span className="text-blue-400">···</span> River</div>
      </div>
    </div>
  )
}
