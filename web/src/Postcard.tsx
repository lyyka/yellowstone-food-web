import type { Postcard } from './types'

type Props = {
  card: Postcard
  onOpen: (id: string) => void
}

export default function Postcard({ card, onOpen }: Props) {
  return (
    <figure className="postcard">
      <div className="postcard-face">
        <span className="postcard-stamp" aria-hidden>
          NPS
        </span>
        {card.image_url ? (
          <img src={card.image_url} alt={card.title} />
        ) : card.photos.length ? (
          <div className={`story-mosaic n-${Math.min(card.photos.length, 4)}`}>
            {card.photos.slice(0, 4).map((src) => (
              <img key={src} src={src} alt="" />
            ))}
          </div>
        ) : (
          <div className="story-ph" />
        )}
        <figcaption className="postcard-banner">
          <p className="kicker">Greetings from Yellowstone</p>
          <h3>{card.title}</h3>
        </figcaption>
      </div>
      <div className="postcard-back">
        <p className="postcard-caption">{card.caption}</p>
        {card.cast.length > 0 && (
          <p className="story-links">
            {card.cast.map((row) => (
              <button key={row.id} type="button" className="chip-btn" onClick={() => onOpen(row.id)}>
                {row.label}
              </button>
            ))}
          </p>
        )}
        <div className="postcard-shop">
          {card.image_url && (
            <a className="back" href={card.image_url} target="_blank" rel="noreferrer">
              Keep a copy
            </a>
          )}
          <button type="button" className="experiment" disabled>
            Gift shop — coming soon
          </button>
        </div>
      </div>
    </figure>
  )
}
