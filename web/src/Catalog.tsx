import { useMemo, useState } from 'react'
import type { CatalogPayload, CatalogSpecies } from './types'

type Props = {
  catalog: CatalogPayload
  onOpen: (id: string) => void
}

const FILTERS = [
  { id: 'all', label: 'All mammals' },
  { id: 'apex', label: 'Hunters' },
  { id: 'mid', label: 'Mid-web' },
  { id: 'prey', label: 'Grazers & prey' },
] as const

function matchesFilter(row: CatalogSpecies, filter: string) {
  const hint = row.trophic_hint || ''
  if (filter === 'apex') return hint.includes('apex') || hint.includes('predator')
  if (filter === 'mid') return hint.includes('mid')
  if (filter === 'prey') return hint.includes('herbivore') || hint.includes('prey')
  return true
}

export default function Catalog({ catalog, onOpen }: Props) {
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['id']>('all')

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return catalog.species.filter((row) => {
      if (!matchesFilter(row, filter)) return false
      if (!needle) return true
      return `${row.common_name} ${row.name} ${row.blurb}`.toLowerCase().includes(needle)
    })
  }, [catalog.species, filter, q])

  const featured = catalog.species.find((s) => s.id === 'canis-lupus')

  return (
    <div className="guide">
      <header className="mast">
        <p className="kicker">Yellowstone mammal field guide</p>
        <h1>Meet a species, then break its web.</h1>
        <p className="lede">
          Each card is one mammal observers actually record in the park. Open it to see only that
          animal’s predators and foods — then ask what happens if it vanishes.
        </p>
      </header>

      {featured && (
        <button type="button" className="featured" onClick={() => onOpen(featured.id)}>
          {featured.photo_url && <img src={featured.photo_url} alt="" />}
          <div>
            <p className="eyebrow">Start here · classic cascade</p>
            <h2>{featured.common_name}</h2>
            <p className="sci">{featured.name}</p>
            <p>{featured.blurb}</p>
            <p className="meta">
              {featured.prey_count} foods · {featured.predator_count} predators ·{' '}
              {featured.observation_count.toLocaleString()} iNaturalist records
            </p>
          </div>
        </button>
      )}

      <div className="toolbar">
        <label>
          Search the guide
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="wolf, elk, beaver…" />
        </label>
        <div className="filters" role="tablist" aria-label="Trophic role">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={filter === f.id ? 'on' : ''}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <p className="count">{rows.length} species in this view</p>

      <ul className="grid">
        {rows.map((row, i) => (
          <li key={row.id} style={{ animationDelay: `${Math.min(i, 16) * 40}ms` }}>
            <button type="button" className="card" onClick={() => onOpen(row.id)}>
              <div className="thumb">
                {row.photo_url ? <img src={row.photo_url} alt="" /> : <span className="placeholder" />}
              </div>
              <div className="body">
                <h3>{row.common_name || row.name}</h3>
                <p className="sci">{row.name}</p>
                <p className="role">{row.trophic_hint}</p>
                <p className="blurb">{row.blurb}</p>
                <p className="meta">
                  Eats {row.prey_count} · eaten by {row.predator_count}
                </p>
              </div>
            </button>
          </li>
        ))}
      </ul>
      <p className="disclaimer">{catalog.disclaimer}</p>
    </div>
  )
}
