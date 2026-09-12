import { useEffect, useMemo, useState } from 'react'
import EgoDiagram from './EgoDiagram'
import RichStory from './RichStory'
import { fetchDossier, removeSpecies } from './api'
import { buildMentionIndex } from './mentions'
import type { Dossier, MentionSpecies, QueryResult } from './types'

type Props = {
  id: string
  mentions: MentionSpecies[]
  onBack: () => void
  onOpen: (id: string) => void
}

export default function SpeciesDossier({ id, mentions, onBack, onOpen }: Props) {
  const [dossier, setDossier] = useState<Dossier | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)

  useEffect(() => {
    setResult(null)
    setError(null)
    fetchDossier(id)
      .then(setDossier)
      .catch((err: Error) => setError(err.message))
  }, [id])

  const localMentions = useMemo(
    () => buildMentionIndex(mentions, dossier?.graph.nodes ?? []),
    [mentions, dossier],
  )

  if (error) {
    return (
      <div className="dossier">
        <button type="button" className="back" onClick={onBack}>
          ← Field guide
        </button>
        <p className="error">{error}</p>
      </div>
    )
  }
  if (!dossier) return <p className="loading">Opening the field notes…</p>

  const sp = dossier.species
  const name = sp.common_name || sp.name
  const removed = result?.removed?.id === sp.id

  const onWhatIf = async () => {
    setBusy(true)
    setError(null)
    try {
      setResult(await removeSpecies(sp.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run the experiment')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="dossier">
      <button type="button" className="back" onClick={onBack}>
        ← Field guide
      </button>

      <section className="hero">
        {sp.photo_url && <img src={sp.photo_url} alt="" />}
        <div>
          <p className="kicker">{sp.in_region ? 'Observed in Yellowstone' : 'Diet partner (GloBI)'}</p>
          <h1>{name}</h1>
          <p className="sci">{sp.name}</p>
          <p className="lede">{dossier.blurb}</p>
          <p className="meta">
            {sp.trophic_hint} · {dossier.eats.length} foods shown · {dossier.eaten_by.length} predators
            shown
            {sp.observation_count ? ` · ${sp.observation_count.toLocaleString()} iNaturalist records` : ''}
          </p>
          {sp.wikipedia_url && (
            <a className="wiki" href={sp.wikipedia_url} target="_blank" rel="noreferrer">
              Encyclopedia page
            </a>
          )}
        </div>
      </section>

      <section className="teach">
        <h2>How to read this page</h2>
        <ol>
          <li>Arrows mean <strong>eats</strong>. Energy in food webs usually flows the other way — up from plants.</li>
          <li>Lists are documented GloBI links, not a complete menu. Missing a food means missing data.</li>
          <li>The experiment removes only this species and colors neighbors that would feel the knock-on.</li>
        </ol>
      </section>

      <div className="split">
        <section>
          <h2>Who eats {name}?</h2>
          {dossier.eaten_by.length === 0 ? (
            <p className="empty">No predators in this snapshot — it may sit near the top of the local web.</p>
          ) : (
            <ul className="rel">
              {dossier.eaten_by.map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => onOpen(n.id)}>
                    {n.photo_url && <img src={n.photo_url} alt="" />}
                    <span>
                      <strong>{n.common_name || n.name}</strong>
                      <em>{n.n_records} records</em>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <h2>What does {name} eat?</h2>
          {dossier.eats.length === 0 ? (
            <p className="empty">No foods recorded here. Try a hunter or a grazer with a longer diet list.</p>
          ) : (
            <ul className="rel">
              {dossier.eats.map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => onOpen(n.id)}>
                    {n.photo_url && <img src={n.photo_url} alt="" />}
                    <span>
                      <strong>{n.common_name || n.name}</strong>
                      <em>
                        {n.kingdom === 'Plantae' ? 'plant · ' : ''}
                        {n.n_records} records
                      </em>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="web-panel">
        <div className="web-head">
          <div>
            <h2>This species’ web</h2>
            <p>Only direct partners — predators above, foods below. Click a box to open that species.</p>
          </div>
          <button type="button" className="experiment" onClick={() => void onWhatIf()} disabled={busy}>
            {busy ? 'Tracing knock-ons…' : `What if we remove ${name}?`}
          </button>
        </div>
        <EgoDiagram
          focus={sp}
          eats={dossier.eats}
          eatenBy={dossier.eaten_by}
          effects={result?.effects || []}
          removed={removed}
          onSelect={onOpen}
        />
        {result?.lesson && (
          <article className="lesson">
            <h3>{result.lesson.title}</h3>
            <RichStory text={result.lesson.blurb} species={localMentions} onOpen={onOpen} />
            {result.llm && <p className="llm">Narrated with Grok</p>}
          </article>
        )}
        {result?.story && (
          <div className="prose">
            {result.story.map((line) => (
              <RichStory key={line} text={line} species={localMentions} onOpen={onOpen} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
