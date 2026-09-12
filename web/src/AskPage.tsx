import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import Postcard from './Postcard'
import RichStory from './RichStory'
import { runScenario } from './api'
import { emptyChat, loadHistory, saveHistory, upsertChat, type Chat, type ChatTurn } from './chatHistory'
import type { ImageModel, MentionSpecies, ScenarioResult } from './types'

const IDEAS = [
  'What if aliens attacked Yellowstone?',
  'What if everyone tried to gray wolf?',
  'What if all the hunters disappeared?',
]

const IMAGE_KEY = 'ask-image-model'

function readImageModel(): ImageModel {
  try {
    const raw = localStorage.getItem(IMAGE_KEY)
    if (raw === 'fal' || raw === 'grok') return raw
  } catch {
    /* ignore */
  }
  return 'grok'
}

type Turn = {
  prompt: string
  result?: ScenarioResult
  error?: string
}

type Props = {
  mentions: MentionSpecies[]
  onOpen: (id: string) => void
  header: ReactNode
}

export default function AskPage({ mentions, onOpen, header }: Props) {
  const initial = useMemo(() => loadHistory(), [])
  const [chats, setChats] = useState<Chat[]>(initial.chats)
  const [activeId, setActiveId] = useState(initial.activeId)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [logOpen, setLogOpen] = useState(false)
  const [imageModel, setImageModel] = useState<ImageModel>(readImageModel)
  const field = useRef<HTMLTextAreaElement>(null)
  const bottom = useRef<HTMLDivElement>(null)

  const active = chats.find((c) => c.id === activeId) ?? { id: activeId, title: 'New what-if', updatedAt: 0, turns: [] }
  const turns = active.turns as Turn[]
  const live = turns.length > 0
  const history = chats.filter((c) => c.turns.length > 0)

  useEffect(() => {
    saveHistory(chats, activeId)
  }, [chats, activeId])

  useEffect(() => {
    try {
      localStorage.setItem(IMAGE_KEY, imageModel)
    } catch {
      /* ignore */
    }
  }, [imageModel])

  useEffect(() => {
    field.current?.focus()
  }, [live, activeId])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, busy, activeId])

  const writeTurns = (nextTurns: ChatTurn[]) => {
    setChats((prev) =>
      upsertChat(prev, {
        id: activeId,
        title: active.title,
        updatedAt: Date.now(),
        turns: nextTurns,
      }),
    )
  }

  const startNew = () => {
    if (busy) return
    const fresh = emptyChat()
    setActiveId(fresh.id)
    setText('')
    setLogOpen(false)
  }

  const openChat = (id: string) => {
    if (busy) return
    setActiveId(id)
    setText('')
    setLogOpen(false)
  }

  const dropChat = (id: string) => {
    setChats((prev) => prev.filter((c) => c.id !== id))
    if (id === activeId) {
      const fresh = emptyChat()
      setActiveId(fresh.id)
    }
  }

  const run = async (prompt: string) => {
    const q = prompt.trim()
    if (!q || busy) return
    setText('')
    setBusy(true)
    const pending = [...turns, { prompt: q }]
    writeTurns(pending)
    try {
      const result = await runScenario(q, imageModel)
      writeTurns([...turns, { prompt: q, result }])
    } catch (err) {
      writeTurns([
        ...turns,
        { prompt: q, error: err instanceof Error ? err.message : 'Scenario failed' },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ask-studio">
      <aside className={`ask-log ${logOpen ? 'open' : ''}`}>
        <div className="ask-log-bar">
          <div>
            <p className="ask-log-mark">Trail register</p>
            <h2>Past what-ifs</h2>
          </div>
          <button type="button" className="ask-log-new" onClick={startNew} disabled={busy || !live}>
            New
          </button>
        </div>
        {history.length === 0 ? (
          <p className="ask-log-empty">Ask a catastrophe and it files itself here — a stack of postcards, not a second menu.</p>
        ) : (
          <ul>
            {history.map((chat) => (
              <li key={chat.id}>
                <button
                  type="button"
                  className={`ask-log-item ${chat.id === activeId ? 'on' : ''}`}
                  onClick={() => openChat(chat.id)}
                >
                  <span>{chat.title}</span>
                  <time>{formatWhen(chat.updatedAt)}</time>
                </button>
                <button
                  type="button"
                  className="ask-log-drop"
                  aria-label={`Delete ${chat.title}`}
                  onClick={() => dropChat(chat.id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <div className="ask-main">
        {header}
        <div className={`ask-root ${live ? 'live' : 'idle'}`}>
        <button type="button" className="ask-log-toggle" onClick={() => setLogOpen((v) => !v)}>
          {logOpen ? 'Hide register' : 'Trail register'}
        </button>
        <div className="ask-scroll">
          {!live && (
            <header className="ask-hero">
              <p className="kicker">Grok + the Yellowstone food web</p>
              <h1>Invent a catastrophe</h1>
              <p className="lede">
                Ask the wildest what-if you can mail home. Real vanishings still run on the park menu;
                daydreams still get a souvenir postcard.
              </p>
            </header>
          )}

          {live && (
            <ol className="ask-thread">
              {turns.map((turn, i) => (
                <li key={`${turn.prompt}-${i}`}>
                  <article className="ask-user">
                    <p className="ask-who">You</p>
                    <p>{turn.prompt}</p>
                  </article>
                  {turn.error && <p className="error">{turn.error}</p>}
                  {turn.result && <ScenarioOut result={turn.result} mentions={mentions} onOpen={onOpen} />}
                  {!turn.result && !turn.error && busy && i === turns.length - 1 && (
                    <p className="ask-wait">
                      Printing your postcard with {imageModel === 'fal' ? 'Fal Flux' : 'Grok Imagine'}…
                    </p>
                  )}
                </li>
              ))}
              <div ref={bottom} />
            </ol>
          )}
        </div>

        <div className="ask-dock">
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault()
              void run(text)
            }}
          >
            <label htmlFor="scenario" className="visually-hidden">
              Your scenario
            </label>
            <textarea
              ref={field}
              id="scenario"
              rows={live ? 2 : 3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void run(text)
                }
              }}
              placeholder={live ? 'Ask another what-if…' : 'What if aliens attacked Yellowstone?'}
            />
            <div className="composer-bar">
              <label className="composer-model">
                <span className="visually-hidden">Postcard model</span>
                <select
                  value={imageModel}
                  disabled={busy}
                  onChange={(e) => setImageModel(e.target.value === 'fal' ? 'fal' : 'grok')}
                >
                  <option value="grok">Grok Imagine</option>
                  <option value="fal">Fal Flux</option>
                </select>
              </label>
              <span className="composer-hint">{busy ? 'Asking…' : 'Enter to ask · Shift+Enter for a line'}</span>
              <button type="submit" className="experiment" disabled={busy || !text.trim()}>
                {busy ? 'Asking' : 'Ask'}
              </button>
            </div>
          </form>
          {!live && (
            <div className="ask-starters">
              {IDEAS.map((idea) => (
                <button key={idea} type="button" className="chip-btn" onClick={() => void run(idea)}>
                  {idea}
                </button>
              ))}
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  )
}

function formatWhen(ts: number) {
  const delta = Date.now() - ts
  if (delta < 60_000) return 'just now'
  if (delta < 3_600_000) return `${Math.floor(delta / 60_000)}m`
  if (delta < 86_400_000) return `${Math.floor(delta / 3_600_000)}h`
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function ScenarioOut({
  result,
  mentions,
  onOpen,
}: {
  result: ScenarioResult
  mentions: MentionSpecies[]
  onOpen: (id: string) => void
}) {
  return (
    <div className="scenario-out">
      <div className="prose">
        {result.story.map((line) => (
          <RichStory key={line} text={line} species={mentions} onOpen={onOpen} />
        ))}
      </div>
      {result.postcard && <Postcard card={result.postcard} onOpen={onOpen} />}
      <Column
        title={
          result.plan.action === 'tell' || result.plan.action === 'imagine'
            ? 'The animal in this story'
            : `Pulled from the park (${result.removed.length})`
        }
        rows={result.removed}
        onOpen={onOpen}
        tone="gone"
      />
      <Column title="Likely released" rows={result.released} onOpen={onOpen} tone="up" />
      <Column title="Under more pressure" rows={result.pressured} onOpen={onOpen} tone="down" />
    </div>
  )
}

function Column({
  title,
  rows,
  onOpen,
  tone,
}: {
  title: string
  rows: { id: string; common_name: string | null; name: string }[]
  onOpen: (id: string) => void
  tone: string
}) {
  if (!rows.length) return null
  return (
    <div className={`bucket ${tone}`}>
      <h3>{title}</h3>
      <ul>
        {rows.slice(0, 10).map((row) => (
          <li key={row.id}>
            <button type="button" onClick={() => onOpen(row.id)}>
              {row.common_name || row.name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
