import { useEffect, useId, useRef, useState } from 'react'
import type { Effect, Neighbor, SpeciesNode } from './types'

type Props = {
  focus: SpeciesNode
  eats: Neighbor[]
  eatenBy: Neighbor[]
  effects: Effect[]
  removed: boolean
  onSelect: (id: string) => void
}

type Peek = {
  node: SpeciesNode
  caption: string
  records?: number
  effect?: Effect
  self?: boolean
}

const WIDTH = 920
const STEP = 118
const RADIUS = 28
const FOCUS_H = 96

function label(node: { common_name: string | null; name: string }) {
  return node.common_name || node.name
}

function colsFor(n: number) {
  if (n <= 1) return 1
  if (n <= 7) return n
  if (n <= 8) return 4
  if (n <= 10) return 5
  return 6
}

function cell(i: number, n: number, y0: number) {
  const cols = colsFor(n)
  const row = Math.floor(i / cols)
  const col = i % cols
  const inRow = Math.min(cols, n - row * cols)
  const pad = 72
  const span = WIDTH - pad * 2
  const x = inRow === 1 ? WIDTH / 2 : pad + (col * span) / Math.max(inRow - 1, 1)
  return { x, y: y0 + row * STEP }
}

function wrapName(raw: string, max = 12): [string, string?] {
  if (raw.length <= max) return [raw]
  const parts = raw.split(/\s+/)
  if (parts.length === 1) return [`${raw.slice(0, max - 1)}…`]
  let first = parts[0]
  let i = 1
  while (i < parts.length && `${first} ${parts[i]}`.length <= max) {
    first = `${first} ${parts[i]}`
    i += 1
  }
  if (i === parts.length) return [raw.length <= max ? raw : first]
  const rest = parts.slice(i).join(' ')
  return [first, rest.length > max ? `${rest.slice(0, max - 1)}…` : rest]
}

export default function EgoDiagram({ focus, eats, eatenBy, effects, removed, onSelect }: Props) {
  const effectMap = new Map(effects.map((e) => [e.node_id, e]))
  const predators = eatenBy
  const foods = eats
  const predRows = predators.length ? Math.ceil(predators.length / colsFor(predators.length)) : 0
  const foodRows = foods.length ? Math.ceil(foods.length / colsFor(foods.length)) : 0
  const predY0 = 42
  const predBlock = predRows ? predRows * STEP + 10 : 18
  const focusY = predBlock + FOCUS_H / 2
  const foodY0 = focusY + FOCUS_H / 2 + 56
  const height = foodY0 + (foodRows ? foodRows * STEP : 40)
  const cx = WIDTH / 2
  const [peek, setPeek] = useState<Peek | null>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  useEffect(() => {
    setPeek(null)
  }, [focus.id])

  const openPeek = (next: Peek) => setPeek(next)
  const closePeek = () => setPeek(null)

  useEffect(() => {
    if (!peek) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePeek()
    }
    window.addEventListener('keydown', onKey)
    dialogRef.current?.querySelector<HTMLElement>('.ego-peek-open, .wiki, .ego-peek-close')?.focus()
    return () => window.removeEventListener('keydown', onKey)
  }, [peek])

  const predPos = predators.map((_, i) => cell(i, predators.length, predY0))
  const foodPos = foods.map((_, i) => cell(i, foods.length, foodY0))

  return (
    <div className="ego-wrap">
      <svg className="ego" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={`Food web around ${label(focus)}`}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#c9b896" />
          </marker>
        </defs>
        {predators.map((p, i) => (
          <line
            key={`pl-${p.id}`}
            x1={predPos[i].x}
            y1={predPos[i].y + RADIUS + 2}
            x2={cx}
            y2={focusY - FOCUS_H / 2 + 4}
            stroke="#c9b896"
            strokeWidth="1.2"
            markerEnd="url(#arrow)"
          />
        ))}
        {foods.map((f, i) => (
          <line
            key={`fl-${f.id}`}
            x1={cx}
            y1={focusY + FOCUS_H / 2 - 4}
            x2={foodPos[i].x}
            y2={foodPos[i].y - RADIUS - 2}
            stroke="#c9b896"
            strokeWidth="1.2"
            markerEnd="url(#arrow)"
          />
        ))}
        {predators.map((p, i) => (
          <PortraitChip
            key={p.id}
            x={predPos[i].x}
            y={predPos[i].y}
            node={p}
            selected={peek?.node.id === p.id}
            effect={removed ? { node_id: p.id, delta_sign: -1, depth: 1, strength: 1, reason: '', common_name: p.common_name, name: p.name, kingdom: p.kingdom } : effectMap.get(p.id)}
            caption="eats this species"
            onPeek={(effect) => openPeek({ node: p, caption: 'eats this species', records: p.n_records, effect })}
          />
        ))}
        <FocusChip
          x={cx}
          y={focusY}
          node={focus}
          removed={removed}
          selected={peek?.node.id === focus.id}
          caption={removed ? 'removed from the web' : 'this species'}
          onPeek={() =>
            openPeek({
              node: focus,
              caption: removed ? 'removed from the web' : 'this species',
              self: true,
            })
          }
        />
        {foods.map((f, i) => (
          <PortraitChip
            key={f.id}
            x={foodPos[i].x}
            y={foodPos[i].y}
            node={f}
            selected={peek?.node.id === f.id}
            effect={removed ? { node_id: f.id, delta_sign: 1, depth: 1, strength: 1, reason: '', common_name: f.common_name, name: f.name, kingdom: f.kingdom } : effectMap.get(f.id)}
            caption={f.kingdom === 'Plantae' ? 'plant food' : 'animal prey'}
            onPeek={(effect) =>
              openPeek({
                node: f,
                caption: f.kingdom === 'Plantae' ? 'plant food' : 'animal prey',
                records: f.n_records,
                effect,
              })
            }
          />
        ))}
      </svg>
      {peek && (
        <div className="ego-peek-scrim" onClick={closePeek}>
          <div
            ref={dialogRef}
            className="ego-peek"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(e) => e.stopPropagation()}
          >
            {peek.node.photo_url ? (
              <img src={peek.node.photo_url} alt="" />
            ) : (
              <div className="tip-ph" aria-hidden />
            )}
            <div>
              <button type="button" className="ego-peek-close" onClick={closePeek} aria-label="Close">
                ×
              </button>
              <p className="ego-peek-role">{peek.caption}</p>
              <h3 id={titleId} className="tip-common">
                {label(peek.node)}
              </h3>
              <p className="tip-sci">{peek.node.name}</p>
              <p className="tip-meta">
                {[
                  peek.node.trophic_hint,
                  peek.node.kingdom === 'Plantae' ? 'plant' : peek.node.kingdom === 'Animalia' ? 'animal' : peek.node.kingdom,
                  peek.node.in_region ? 'seen in Yellowstone' : 'diet partner',
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              {peek.records != null && (
                <p className="tip-meta">{peek.records.toLocaleString()} GloBI diet records in this snapshot</p>
              )}
              {peek.node.observation_count > 0 && (
                <p className="tip-meta">{peek.node.observation_count.toLocaleString()} iNaturalist records</p>
              )}
              {peek.effect && (
                <p className={peek.effect.delta_sign > 0 ? 'ego-peek-up' : 'ego-peek-down'}>
                  {peek.effect.delta_sign > 0 ? 'Likely increases' : 'Under more pressure'}
                  {peek.effect.reason ? ` — ${peek.effect.reason}` : ''}
                </p>
              )}
              <div className="ego-peek-actions">
                {peek.self ? (
                  <p className="tip-cta">You are already on this page</p>
                ) : (
                  <button
                    type="button"
                    className="ego-peek-open"
                    onClick={() => {
                      closePeek()
                      onSelect(peek.node.id)
                    }}
                  >
                    Open field notes
                  </button>
                )}
                {peek.node.wikipedia_url && (
                  <a className="wiki" href={peek.node.wikipedia_url} target="_blank" rel="noreferrer">
                    Encyclopedia
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function FocusChip({
  x,
  y,
  node,
  removed,
  selected,
  caption,
  onPeek,
}: {
  x: number
  y: number
  node: SpeciesNode
  removed?: boolean
  selected?: boolean
  caption: string
  onPeek: () => void
}) {
  const photo = node.photo_url
  const w = 236
  const h = FOCUS_H
  const portrait = 58
  const clipId = `chip-focus-${node.id}`
  const px = 9
  const py = h / 2
  const fill = removed ? '#efe6d0' : '#24352c'
  const stroke = selected ? '#efe6d0' : '#c45c26'
  const text = removed ? '#132019' : '#f4efe4'
  const name = wrapName(label(node), 16)
  return (
    <g
      className={`chip-node${selected ? ' is-open' : ''}`}
      transform={`translate(${x - w / 2}, ${y - h / 2})`}
      role="button"
      tabIndex={0}
      aria-haspopup="dialog"
      aria-label={`${label(node)}. ${caption}. Open quick info.`}
      onClick={onPeek}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onPeek()
        }
      }}
    >
      <title>{label(node)}</title>
      <rect width={w} height={h} rx="8" fill={fill} stroke={stroke} strokeWidth="2.2" />
      {photo && (
        <>
          <clipPath id={clipId}>
            <circle cx={px + portrait / 2} cy={py} r={portrait / 2} />
          </clipPath>
          <image
            href={photo}
            x={px}
            y={py - portrait / 2}
            width={portrait}
            height={portrait}
            clipPath={`url(#${clipId})`}
            preserveAspectRatio="xMidYMid slice"
            opacity={removed ? 0.45 : 1}
          />
          <circle cx={px + portrait / 2} cy={py} r={portrait / 2} fill="none" stroke={stroke} strokeWidth="1.6" />
        </>
      )}
      <text x={photo ? 78 : w / 2} y={40} textAnchor={photo ? 'start' : 'middle'} fill={text} fontSize="16" fontFamily="Fraunces, Georgia, serif">
        {name[0]}
      </text>
      {name[1] ? (
        <text x={photo ? 78 : w / 2} y={58} textAnchor={photo ? 'start' : 'middle'} fill={text} fontSize="16" fontFamily="Fraunces, Georgia, serif">
          {name[1]}
        </text>
      ) : (
        <text x={photo ? 78 : w / 2} y={62} textAnchor={photo ? 'start' : 'middle'} fill={removed ? '#5d4c3a' : '#c9b896'} fontSize="10">
          {caption}
        </text>
      )}
    </g>
  )
}

function PortraitChip({
  x,
  y,
  node,
  effect,
  selected,
  caption,
  onPeek,
}: {
  x: number
  y: number
  node: SpeciesNode
  effect?: Effect
  selected?: boolean
  caption: string
  onPeek: (effect?: Effect) => void
}) {
  const photo = node.photo_url
  const clipId = `chip-port-${node.id}-${caption.replace(/\s+/g, '-')}`
  let ring = selected ? '#efe6d0' : '#9cbf6b'
  if (effect?.delta_sign === 1) ring = '#8dffb0'
  if (effect?.delta_sign === -1) ring = '#ffb3a3'
  const fill = node.kingdom === 'Plantae' ? '#2d4a32' : '#24352c'
  const lines = wrapName(label(node), 11)
  const activate = () => onPeek(effect)
  const initial = (node.common_name || node.name).slice(0, 1).toUpperCase()
  return (
    <g
      className={`chip-node${selected ? ' is-open' : ''}`}
      transform={`translate(${x}, ${y})`}
      role="button"
      tabIndex={0}
      aria-haspopup="dialog"
      aria-label={`${label(node)}. ${caption}. Open quick info.`}
      onClick={activate}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          activate()
        }
      }}
    >
      <title>{label(node)}</title>
      <circle r={RADIUS + 10} fill="transparent" />
      {photo ? (
        <>
          <clipPath id={clipId}>
            <circle r={RADIUS} />
          </clipPath>
          <image
            href={photo}
            x={-RADIUS}
            y={-RADIUS}
            width={RADIUS * 2}
            height={RADIUS * 2}
            clipPath={`url(#${clipId})`}
            preserveAspectRatio="xMidYMid slice"
          />
        </>
      ) : (
        <>
          <circle r={RADIUS} fill={fill} />
          <text textAnchor="middle" y="6" fill="#c9b896" fontSize="16" fontFamily="Fraunces, Georgia, serif">
            {initial}
          </text>
        </>
      )}
      <circle r={RADIUS} fill="none" stroke={ring} strokeWidth={selected ? 2.4 : 1.6} />
      <text y={RADIUS + 16} textAnchor="middle" fill="#f4efe4" fontSize="11" fontFamily="Fraunces, Georgia, serif">
        {lines[0]}
      </text>
      {lines[1] && (
        <text y={RADIUS + 30} textAnchor="middle" fill="#f4efe4" fontSize="11" fontFamily="Fraunces, Georgia, serif">
          {lines[1]}
        </text>
      )}
    </g>
  )
}
