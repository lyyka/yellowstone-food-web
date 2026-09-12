import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { splitMentions } from './mentions'
import type { MentionSpecies } from './types'

type Props = {
  text: string
  species: MentionSpecies[]
  onOpen: (id: string) => void
}

export default function RichStory({ text, species, onOpen }: Props) {
  const parts = splitMentions(text, species)
  return (
    <p className="prose-line">
      {parts.map((part, i) =>
        part.species ? (
          <SpeciesMention key={`${part.species.id}-${i}`} species={part.species} label={part.text} onOpen={onOpen} />
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </p>
  )
}

function SpeciesMention({
  species,
  label,
  onOpen,
}: {
  species: MentionSpecies
  label: string
  onOpen: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const btn = useRef<HTMLButtonElement>(null)
  const hide = useRef<number | null>(null)
  const tipId = useId()

  const show = () => {
    if (hide.current) window.clearTimeout(hide.current)
    const box = btn.current?.getBoundingClientRect()
    if (box) {
      const width = 280
      const left = Math.min(Math.max(12, box.left + box.width / 2 - width / 2), window.innerWidth - width - 12)
      const below = box.bottom + 10
      const top = below + 220 > window.innerHeight ? Math.max(12, box.top - 230) : below
      setPos({ top, left })
    }
    setOpen(true)
  }

  const delayHide = () => {
    hide.current = window.setTimeout(() => setOpen(false), 140)
  }

  useEffect(() => () => {
    if (hide.current) window.clearTimeout(hide.current)
  }, [])

  return (
    <>
      <button
        ref={btn}
        type="button"
        className={`mention ${species.kingdom === 'Plantae' ? 'plant' : 'animal'}`}
        aria-describedby={open ? tipId : undefined}
        onMouseEnter={show}
        onMouseLeave={delayHide}
        onFocus={show}
        onBlur={delayHide}
        onClick={() => onOpen(species.id)}
      >
        {label}
      </button>
      {open &&
        createPortal(
          <aside
            id={tipId}
            className="species-tip"
            style={{ top: pos.top, left: pos.left }}
            onMouseEnter={show}
            onMouseLeave={delayHide}
          >
            {species.photo_url ? (
              <img src={species.photo_url} alt="" />
            ) : (
              <div className="tip-ph" />
            )}
            <div>
              <p className="tip-common">{species.common_name || species.name}</p>
              <p className="tip-sci">{species.name}</p>
              <p className="tip-blurb">{species.blurb}</p>
              {(species.prey_count != null || species.predator_count != null) && (
                <p className="tip-meta">
                  Eats {species.prey_count ?? 0} · eaten by {species.predator_count ?? 0}
                </p>
              )}
              <p className="tip-cta">Open field notes</p>
            </div>
          </aside>,
          document.body,
        )}
    </>
  )
}
