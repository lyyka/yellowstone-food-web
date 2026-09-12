import { useEffect, useMemo, useState } from 'react'
import AlbumPage from './AlbumPage'
import AskPage from './AskPage'
import Catalog from './Catalog'
import ManagePage from './ManagePage'
import SpeciesDossier from './SpeciesDossier'
import { fetchCatalog, fetchGraph } from './api'
import { buildMentionIndex } from './mentions'
import type { CatalogPayload, MentionSpecies, SpeciesNode } from './types'
import './App.css'

type Route =
  | { page: 'ask' }
  | { page: 'guide' }
  | { page: 'album' }
  | { page: 'manage' }
  | { page: 'species'; id: string }

function readRoute(): Route {
  const raw = window.location.hash.replace(/^#\/?/, '')
  if (!raw || raw === 'ask') return { page: 'ask' }
  if (raw === 'guide') return { page: 'guide' }
  if (raw === 'album') return { page: 'album' }
  if (raw === 'manage') return { page: 'manage' }
  return { page: 'species', id: raw }
}

export default function App() {
  const [catalog, setCatalog] = useState<CatalogPayload | null>(null)
  const [graphNodes, setGraphNodes] = useState<SpeciesNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [route, setRoute] = useState<Route>(readRoute)

  const reloadLists = () => {
    fetchCatalog()
      .then(setCatalog)
      .catch((err: Error) => setError(err.message))
    fetchGraph()
      .then((g) => setGraphNodes(g.nodes))
      .catch(() => setGraphNodes([]))
  }

  useEffect(() => {
    reloadLists()
  }, [])

  useEffect(() => {
    const onHash = () => setRoute(readRoute())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const mentions: MentionSpecies[] = useMemo(
    () => buildMentionIndex(catalog?.species ?? [], graphNodes),
    [catalog, graphNodes],
  )

  const go = (hash: string) => {
    window.location.hash = hash
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const open = (id: string) => go(`/${id}`)

  const nav = (
    <nav className="topnav">
      <a href="#/" className={route.page === 'ask' ? 'on' : ''}>
        Ask the web
      </a>
      <a href="#/guide" className={route.page === 'guide' || route.page === 'species' ? 'on' : ''}>
        Field guide
      </a>
      <a href="#/album" className={route.page === 'album' ? 'on' : ''}>
        Album
      </a>
      <a href="#/manage" className={route.page === 'manage' ? 'on' : ''}>
        Ledger
      </a>
    </nav>
  )

  return (
    <div className={route.page === 'ask' ? 'frame ask-frame' : 'frame'}>
      <div className="grain" aria-hidden />
      {error && <p className="error banner">{error}</p>}
      {route.page === 'ask' ? (
        <AskPage mentions={mentions} onOpen={open} header={nav} />
      ) : (
        <>
          {nav}
        <div className="shell">
          {route.page === 'manage' ? (
            <ManagePage onChanged={reloadLists} />
          ) : route.page === 'album' ? (
            <AlbumPage onOpen={open} />
          ) : route.page === 'species' ? (
            <SpeciesDossier
              key={route.id}
              id={route.id}
              mentions={mentions}
              onBack={() => go('/guide')}
              onOpen={open}
            />
          ) : catalog ? (
            <Catalog catalog={catalog} onOpen={open} />
          ) : (
            <p className="loading">Gathering the park checklist…</p>
          )}
        </div>
        </>
      )}
    </div>
  )
}
