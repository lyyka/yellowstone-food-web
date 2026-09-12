import { loadHistory, type ChatTurn } from './chatHistory'
import type { Postcard } from './types'

const KEY = 'postcard-album'
const MIGRATED = 'postcard-album-migrated'

export type SavedPostcard = {
  id: string
  prompt: string
  savedAt: number
  card: Postcard
}

function uid() {
  return crypto.randomUUID?.() ?? `pc-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function fingerprint(prompt: string, card: Postcard) {
  return `${prompt.trim()}::${card.title}::${card.image_url || card.photos[0] || card.caption}`
}

function readStore(): SavedPostcard[] {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? (JSON.parse(raw) as SavedPostcard[]) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeStore(rows: SavedPostcard[]) {
  localStorage.setItem(KEY, JSON.stringify(rows))
}

function postcardFromTurn(turn: ChatTurn): Postcard | null {
  const result = turn.result as { postcard?: Postcard } | undefined
  return result?.postcard ?? null
}

function mergeFromChats(existing: SavedPostcard[]): SavedPostcard[] {
  const seen = new Set(existing.map((row) => fingerprint(row.prompt, row.card)))
  const extra: SavedPostcard[] = []
  for (const chat of loadHistory().chats) {
    for (const turn of chat.turns) {
      const card = postcardFromTurn(turn)
      if (!card) continue
      const key = fingerprint(turn.prompt, card)
      if (seen.has(key)) continue
      seen.add(key)
      extra.push({
        id: uid(),
        prompt: turn.prompt,
        savedAt: chat.updatedAt,
        card,
      })
    }
  }
  return extra.length ? [...extra, ...existing] : existing
}

export function loadAlbum(): SavedPostcard[] {
  let rows = readStore()
  try {
    if (!localStorage.getItem(MIGRATED)) {
      rows = mergeFromChats(rows)
      writeStore(rows)
      localStorage.setItem(MIGRATED, '1')
    }
  } catch {
    /* private mode */
  }
  return [...rows].sort((a, b) => b.savedAt - a.savedAt)
}

export function rememberPostcard(prompt: string, card: Postcard) {
  const rows = readStore()
  const key = fingerprint(prompt, card)
  if (rows.some((row) => fingerprint(row.prompt, row.card) === key)) return
  writeStore([{ id: uid(), prompt, savedAt: Date.now(), card }, ...rows])
}

export function dropPostcard(id: string) {
  writeStore(readStore().filter((row) => row.id !== id))
}
