const CHATS_KEY = 'ask-chats'
const ACTIVE_KEY = 'ask-active'
const LEGACY_KEY = 'ask-turns'

export type ChatTurn = {
  prompt: string
  result?: unknown
  error?: string
}

export type Chat = {
  id: string
  title: string
  updatedAt: number
  turns: ChatTurn[]
}

function uid() {
  return crypto.randomUUID?.() ?? `chat-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function titleFrom(turns: ChatTurn[]): string {
  const first = turns[0]?.prompt.trim() || 'Untitled what-if'
  return first.length > 52 ? `${first.slice(0, 49)}…` : first
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export function loadHistory(): { chats: Chat[]; activeId: string } {
  let chats = readJson<Chat[]>(CHATS_KEY, [])
  if (!Array.isArray(chats)) chats = []

  if (!chats.length) {
    try {
      const legacy = sessionStorage.getItem(LEGACY_KEY)
      const turns = legacy ? (JSON.parse(legacy) as ChatTurn[]) : []
      if (turns.length) {
        const chat: Chat = {
          id: uid(),
          title: titleFrom(turns),
          updatedAt: Date.now(),
          turns,
        }
        chats = [chat]
        sessionStorage.removeItem(LEGACY_KEY)
      }
    } catch {
      /* ignore broken legacy */
    }
  }

  const storedActive = localStorage.getItem(ACTIVE_KEY)
  const activeId = chats.some((c) => c.id === storedActive) ? storedActive! : chats[0]?.id ?? uid()
  return { chats, activeId }
}

export function saveHistory(chats: Chat[], activeId: string) {
  const kept = chats.filter((c) => c.turns.length > 0)
  localStorage.setItem(CHATS_KEY, JSON.stringify(kept))
  localStorage.setItem(ACTIVE_KEY, activeId)
}

export function emptyChat(): Chat {
  return { id: uid(), title: 'New what-if', updatedAt: Date.now(), turns: [] }
}

export function upsertChat(chats: Chat[], chat: Chat): Chat[] {
  const titled = {
    ...chat,
    title: chat.turns.length ? titleFrom(chat.turns) : chat.title,
    updatedAt: Date.now(),
  }
  const rest = chats.filter((c) => c.id !== chat.id)
  return titled.turns.length ? [titled, ...rest] : rest
}
