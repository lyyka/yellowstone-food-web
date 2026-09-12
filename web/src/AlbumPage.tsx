import { useMemo, useState } from 'react'
import Postcard from './Postcard'
import { dropPostcard, loadAlbum, type SavedPostcard } from './postcardAlbum'

type Props = {
  onOpen: (id: string) => void
}

export default function AlbumPage({ onOpen }: Props) {
  const [rows, setRows] = useState(() => loadAlbum())
  const [open, setOpen] = useState<SavedPostcard | null>(null)
  const count = rows.length
  const heading = useMemo(() => (count === 1 ? '1 souvenir' : `${count} souvenirs`), [count])

  const refresh = () => setRows(loadAlbum())

  return (
    <div className="album">
      <header className="mast">
        <p className="kicker">Gift-shop counter</p>
        <h1>Postcard album</h1>
        <p className="lede">
          Every what-if you printed on Ask files itself here — a rack of Yellowstone souvenirs you
          could almost buy.
        </p>
        <p className="meta">{heading}</p>
      </header>

      {rows.length === 0 ? (
        <p className="album-empty">
          The rack is empty. <a href="#/">Ask a wild what-if</a> and the print lands here.
        </p>
      ) : (
        <ul className="album-grid">
          {rows.map((row, i) => (
            <li key={row.id}>
              <button type="button" className={`album-tile t-${i % 5}`} onClick={() => setOpen(row)}>
                <span className="postcard-stamp" aria-hidden>
                  NPS
                </span>
                {row.card.image_url ? (
                  <img src={row.card.image_url} alt="" />
                ) : row.card.photos.length ? (
                  <img src={row.card.photos[0]} alt="" />
                ) : (
                  <div className="story-ph" />
                )}
                <span className="album-tile-cap">
                  <em>Greetings from Yellowstone</em>
                  <strong>{row.card.title}</strong>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {open && (
        <div className="album-scrim" onClick={() => setOpen(null)}>
          <div className="album-lightbox" role="dialog" aria-modal="true" aria-label={open.card.title} onClick={(e) => e.stopPropagation()}>
            <p className="album-prompt">You asked: {open.prompt}</p>
            <Postcard card={open.card} onOpen={onOpen} />
            <div className="album-lightbox-actions">
              <button type="button" className="back" onClick={() => setOpen(null)}>
                Close
              </button>
              <button
                type="button"
                className="back"
                onClick={() => {
                  dropPostcard(open.id)
                  setOpen(null)
                  refresh()
                }}
              >
                Remove from album
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
