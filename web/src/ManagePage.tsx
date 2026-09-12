import { useEffect, useMemo, useState } from 'react'
import {
  createSpecies,
  deleteSpecies,
  fetchLedger,
  importSpeciesCsv,
  updateSpecies,
} from './api'
import type { LedgerSpecies } from './types'

const BLANK = {
  name: '',
  common_name: '',
  rank: 'species',
  kingdom: 'Animalia',
  trophic_hint: '',
  in_region: true,
  photo_url: '',
  wikipedia_url: '',
  observation_count: '0',
  eats: '',
}

type FormState = typeof BLANK

function toForm(row: LedgerSpecies): FormState {
  return {
    name: row.name,
    common_name: row.common_name || '',
    rank: row.rank,
    kingdom: row.kingdom || '',
    trophic_hint: row.trophic_hint || '',
    in_region: row.in_region,
    photo_url: row.photo_url || '',
    wikipedia_url: row.wikipedia_url || '',
    observation_count: String(row.observation_count ?? 0),
    eats: (row.eats || []).join(', '),
  }
}

function toBody(form: FormState) {
  return {
    name: form.name.trim(),
    common_name: form.common_name.trim() || null,
    rank: form.rank.trim() || 'species',
    kingdom: form.kingdom.trim() || null,
    trophic_hint: form.trophic_hint.trim() || null,
    in_region: form.in_region,
    photo_url: form.photo_url.trim() || null,
    wikipedia_url: form.wikipedia_url.trim() || null,
    observation_count: Number(form.observation_count) || 0,
    eats: form.eats
      .split(/[;,]/)
      .map((part) => part.trim())
      .filter(Boolean),
  }
}

type Props = {
  onChanged: () => void
}

export default function ManagePage({ onChanged }: Props) {
  const [rows, setRows] = useState<LedgerSpecies[]>([])
  const [q, setQ] = useState('')
  const [scope, setScope] = useState<'all' | 'park' | 'partners'>('all')
  const [editing, setEditing] = useState<string | 'new' | null>(null)
  const [form, setForm] = useState<FormState>(BLANK)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    const data = await fetchLedger()
    setRows(data.species)
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message))
  }, [])

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return rows.filter((row) => {
      if (scope === 'park' && !row.in_region) return false
      if (scope === 'partners' && row.in_region) return false
      if (!needle) return true
      return `${row.common_name} ${row.name} ${row.id}`.toLowerCase().includes(needle)
    })
  }, [rows, q, scope])

  const openNew = () => {
    setEditing('new')
    setForm(BLANK)
    setError(null)
  }

  const openEdit = (row: LedgerSpecies) => {
    setEditing(row.id)
    setForm(toForm(row))
    setError(null)
  }

  const save = async () => {
    setBusy(true)
    setError(null)
    try {
      if (editing === 'new') await createSpecies(toBody(form))
      else if (editing) await updateSpecies(editing, toBody(form))
      setEditing(null)
      setNotice(editing === 'new' ? 'Added to the ledger.' : 'Specimen updated.')
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (row: LedgerSpecies) => {
    const label = row.common_name || row.name
    if (!window.confirm(`Remove ${label} from the ledger? Diet links to it will be dropped.`)) return
    setBusy(true)
    try {
      await deleteSpecies(row.id)
      if (editing === row.id) setEditing(null)
      setNotice(`${label} removed.`)
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  const onImport = async (file: File) => {
    setBusy(true)
    setError(null)
    try {
      const report = await importSpeciesCsv(file)
      setNotice(
        `Import finished: ${report.created} added, ${report.updated} updated` +
          (report.errors.length ? `, ${report.errors.length} row errors` : '') +
          (report.skipped_eats.length ? `. Unmatched foods: ${report.skipped_eats.slice(0, 6).join(', ')}` : '.'),
      )
      if (report.errors.length) setError(report.errors.slice(0, 4).join(' · '))
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ledger">
      <header className="ledger-head">
        <div>
          <p className="kicker">Specimen ledger</p>
          <h1>Keep the park list honest.</h1>
          <p className="lede">
            Add, edit, or retire species. The field guide only shows rows marked as on the park checklist.
            Diet goes in <em>eats</em> as scientific names, common names, or ids.
          </p>
        </div>
        <div className="ledger-actions">
          <a className="back" href="/api/admin/species/template.csv" download="species-ledger-example.csv">
            Download example CSV
          </a>
          <a className="back" href="/api/admin/species/export.csv" download="species-ledger.csv">
            Export ledger
          </a>
          <label className="file-btn">
            Import CSV
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void onImport(file)
                e.target.value = ''
              }}
            />
          </label>
          <button type="button" className="experiment" onClick={openNew}>
            New species
          </button>
        </div>
      </header>

      {notice && <p className="ledger-note">{notice}</p>}
      {error && <p className="error">{error}</p>}

      <div className="toolbar">
        <label>
          Search the ledger
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="wolf, Salix, puma…" />
        </label>
        <div className="filters" role="tablist" aria-label="Ledger scope">
          {(
            [
              ['all', 'All records'],
              ['park', 'Park checklist'],
              ['partners', 'Diet partners'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={scope === id}
              className={scope === id ? 'on' : ''}
              onClick={() => setScope(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <p className="count">
        {visible.length} of {rows.length} records
      </p>

      <div className="ledger-layout">
        <div className="ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Common</th>
                <th>Scientific</th>
                <th>Role</th>
                <th>Park</th>
                <th>Eats</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id} className={editing === row.id ? 'on' : ''}>
                  <td>
                    <button type="button" className="linkish" onClick={() => openEdit(row)}>
                      {row.common_name || '—'}
                    </button>
                  </td>
                  <td className="sci">{row.name}</td>
                  <td>{row.trophic_hint || row.kingdom}</td>
                  <td>{row.in_region ? 'yes' : '—'}</td>
                  <td>{row.prey_count}</td>
                  <td>
                    <button type="button" className="back" onClick={() => void remove(row)} disabled={busy}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {editing && (
          <form
            className="ledger-form"
            onSubmit={(e) => {
              e.preventDefault()
              void save()
            }}
          >
            <p className="eyebrow">{editing === 'new' ? 'Accession' : 'Revise specimen'}</p>
            <label>
              Scientific name
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Canis lupus"
              />
            </label>
            <label>
              Common name
              <input
                value={form.common_name}
                onChange={(e) => setForm({ ...form, common_name: e.target.value })}
                placeholder="Gray Wolf"
              />
            </label>
            <div className="form-row">
              <label>
                Rank
                <input value={form.rank} onChange={(e) => setForm({ ...form, rank: e.target.value })} />
              </label>
              <label>
                Kingdom
                <input value={form.kingdom} onChange={(e) => setForm({ ...form, kingdom: e.target.value })} />
              </label>
            </div>
            <label>
              Trophic hint
              <input
                value={form.trophic_hint}
                onChange={(e) => setForm({ ...form, trophic_hint: e.target.value })}
                placeholder="mid-web"
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.in_region}
                onChange={(e) => setForm({ ...form, in_region: e.target.checked })}
              />
              On the Yellowstone park checklist
            </label>
            <label>
              Eats (comma-separated)
              <textarea
                rows={3}
                value={form.eats}
                onChange={(e) => setForm({ ...form, eats: e.target.value })}
                placeholder="Cervus canadensis, Salix"
              />
            </label>
            <label>
              Photo URL
              <input value={form.photo_url} onChange={(e) => setForm({ ...form, photo_url: e.target.value })} />
            </label>
            <label>
              Wikipedia URL
              <input
                value={form.wikipedia_url}
                onChange={(e) => setForm({ ...form, wikipedia_url: e.target.value })}
              />
            </label>
            <div className="form-row">
              <button type="submit" className="experiment" disabled={busy || !form.name.trim()}>
                {busy ? 'Saving…' : editing === 'new' ? 'Add to ledger' : 'Save changes'}
              </button>
              <button type="button" className="back" onClick={() => setEditing(null)}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
