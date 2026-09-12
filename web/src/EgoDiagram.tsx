import type { Effect, Neighbor, SpeciesNode } from './types'

type Props = {
  focus: SpeciesNode
  eats: Neighbor[]
  eatenBy: Neighbor[]
  effects: Effect[]
  removed: boolean
  onSelect: (id: string) => void
}

function label(node: { common_name: string | null; name: string }) {
  return node.common_name || node.name
}

export default function EgoDiagram({ focus, eats, eatenBy, effects, removed, onSelect }: Props) {
  const effectMap = new Map(effects.map((e) => [e.node_id, e]))
  const predators = eatenBy.slice(0, 8)
  const foods = eats.slice(0, 12)
  const width = 920
  const rowH = 118
  const top = predators.length ? 130 : 36
  const height = top + 160 + (foods.length ? Math.ceil(foods.length / 6) * rowH + 24 : 48)
  const cx = width / 2

  const predX = (i: number) =>
    predators.length === 1 ? cx : 90 + (i * (width - 180)) / Math.max(predators.length - 1, 1)
  const foodPos = (i: number) => {
    const row = Math.floor(i / 6)
    const col = i % 6
    const count = Math.min(6, foods.length - row * 6)
    const span = width - 120
    const x = 60 + (count === 1 ? span / 2 : (col * span) / Math.max(count - 1, 1))
    return { x, y: top + 170 + row * rowH }
  }

  return (
    <svg className="ego" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Food web around ${label(focus)}`}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#c9b896" />
        </marker>
      </defs>
      {predators.map((p, i) => (
        <line
          key={`pl-${p.id}`}
          x1={predX(i)}
          y1={86}
          x2={cx}
          y2={top + 8}
          stroke="#c9b896"
          strokeWidth="1.4"
          markerEnd="url(#arrow)"
        />
      ))}
      {foods.map((f, i) => {
        const { x, y } = foodPos(i)
        return (
          <line
            key={`fl-${f.id}`}
            x1={cx}
            y1={top + 92}
            x2={x}
            y2={y - 34}
            stroke="#c9b896"
            strokeWidth="1.4"
            markerEnd="url(#arrow)"
          />
        )
      })}
      {predators.map((p, i) => (
        <SpeciesChip
          key={p.id}
          x={predX(i)}
          y={52}
          node={p}
          effect={removed ? { node_id: p.id, delta_sign: -1, depth: 1, strength: 1, reason: '', common_name: p.common_name, name: p.name, kingdom: p.kingdom } : effectMap.get(p.id)}
          caption="eats this species"
          onSelect={onSelect}
        />
      ))}
      <SpeciesChip
        x={cx}
        y={top + 50}
        node={focus}
        featured
        removed={removed}
        caption={removed ? 'removed from the web' : 'this species'}
        onSelect={onSelect}
      />
      {foods.map((f, i) => {
        const { x, y } = foodPos(i)
        return (
          <SpeciesChip
            key={f.id}
            x={x}
            y={y}
            node={f}
            effect={removed ? { node_id: f.id, delta_sign: 1, depth: 1, strength: 1, reason: '', common_name: f.common_name, name: f.name, kingdom: f.kingdom } : effectMap.get(f.id)}
            caption={f.kingdom === 'Plantae' ? 'plant food' : 'animal prey'}
            onSelect={onSelect}
          />
        )
      })}
    </svg>
  )
}

function SpeciesChip({
  x,
  y,
  node,
  effect,
  featured,
  removed,
  caption,
  onSelect,
}: {
  x: number
  y: number
  node: SpeciesNode
  effect?: Effect
  featured?: boolean
  removed?: boolean
  caption: string
  onSelect: (id: string) => void
}) {
  const w = featured ? 210 : 128
  const h = featured ? 86 : 64
  let fill = '#24352c'
  if (node.kingdom === 'Plantae') fill = '#2d4a32'
  if (effect?.delta_sign === 1) fill = '#1f5c3a'
  if (effect?.delta_sign === -1) fill = '#6b2e22'
  if (removed) fill = '#efe6d0'
  const stroke = featured ? '#c45c26' : '#9cbf6b'
  const text = removed ? '#132019' : '#f4efe4'
  return (
    <g className="chip-node" transform={`translate(${x - w / 2}, ${y - h / 2})`} onClick={() => onSelect(node.id)}>
      <rect width={w} height={h} rx="6" fill={fill} stroke={stroke} strokeWidth={featured ? 2.2 : 1} />
      <text x={w / 2} y={featured ? 34 : 26} textAnchor="middle" fill={text} fontSize={featured ? 16 : 12} fontFamily="Fraunces, Georgia, serif">
        {(node.common_name || node.name).slice(0, 22)}
      </text>
      <text x={w / 2} y={featured ? 54 : 44} textAnchor="middle" fill={removed ? '#5d4c3a' : '#c9b896'} fontSize="10">
        {caption}
      </text>
      {effect && (
        <text x={w / 2} y={featured ? 72 : 58} textAnchor="middle" fill={effect.delta_sign > 0 ? '#8dffb0' : '#ffb3a3'} fontSize="10">
          {effect.delta_sign > 0 ? 'likely increases' : 'under more pressure'}
        </text>
      )}
    </g>
  )
}
