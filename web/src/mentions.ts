import type { CatalogSpecies, MentionSpecies, SpeciesNode } from './types'

const ALIASES: Record<string, string> = {
  wolf: 'canis-lupus',
  wolves: 'canis-lupus',
  'gray wolf': 'canis-lupus',
  'grey wolf': 'canis-lupus',
  elk: 'cervus-canadensis',
  wapiti: 'cervus-canadensis',
  moose: 'alces-alces',
  bison: 'bos-bison',
  buffalo: 'bos-bison',
  coyote: 'canis-latrans',
  coyotes: 'canis-latrans',
  cougar: 'puma-concolor',
  'mountain lion': 'puma-concolor',
  'mountain lions': 'puma-concolor',
  puma: 'puma-concolor',
  bear: 'ursus-arctos',
  bears: 'ursus-arctos',
  'brown bear': 'ursus-arctos',
  'brown bears': 'ursus-arctos',
  'grizzly bear': 'ursus-arctos',
  grizzly: 'ursus-arctos',
  'black bear': 'ursus-americanus',
  beaver: 'castor-canadensis',
  beavers: 'castor-canadensis',
  aspen: 'populus-tremuloides',
  willow: 'salix',
  willows: 'salix',
  'mule deer': 'odocoileus-hemionus',
  deer: 'odocoileus-hemionus',
  'white-tailed deer': 'odocoileus-virginianus',
  lynx: 'lynx-canadensis',
  fox: 'vulpes-vulpes',
  'red fox': 'vulpes-vulpes',
  pronghorn: 'antilocapra-americana',
  otter: 'lontra-canadensis',
  mink: 'neogale-vison',
}

export function buildMentionIndex(
  catalog: Array<CatalogSpecies | MentionSpecies>,
  extras: SpeciesNode[] = [],
): MentionSpecies[] {
  const byId = new Map<string, MentionSpecies>()
  for (const node of extras) {
    byId.set(node.id, {
      id: node.id,
      name: node.name,
      common_name: node.common_name,
      kingdom: node.kingdom,
      trophic_hint: node.trophic_hint,
      blurb: node.trophic_hint
        ? `${node.common_name || node.name} — ${node.trophic_hint}.`
        : `${node.common_name || node.name} (${node.name})`,
      photo_url: node.photo_url,
      observation_count: node.observation_count,
    })
  }
  for (const row of catalog) {
    byId.set(row.id, {
      id: row.id,
      name: row.name,
      common_name: row.common_name,
      kingdom: row.kingdom,
      trophic_hint: row.trophic_hint,
      blurb: row.blurb,
      photo_url: row.photo_url,
      prey_count: 'prey_count' in row ? row.prey_count : undefined,
      predator_count: 'predator_count' in row ? row.predator_count : undefined,
      observation_count: row.observation_count,
    })
  }
  return [...byId.values()]
}

function plurals(name: string): string[] {
  const base = name.trim()
  if (!base) return []
  const lower = base.toLowerCase()
  if (
    lower.endsWith('deer') ||
    lower.endsWith('moose') ||
    lower.endsWith('sheep') ||
    lower.endsWith('bison')
  ) {
    return []
  }
  if (lower.endsWith('wolf')) return [`${base.slice(0, -4)}wolves`]
  if (lower.endsWith('fox') || lower.endsWith('lynx')) return [`${base}es`]
  if (lower.endsWith('s')) return []
  return [`${base}s`]
}

function resolveAlias(byId: Map<string, MentionSpecies>, id: string): MentionSpecies | undefined {
  const exact = byId.get(id)
  if (exact) return exact
  return [...byId.values()].find((s) => s.id === id || s.id.startsWith(`${id}-`))
}

export function mentionPatterns(index: MentionSpecies[]): { phrase: string; species: MentionSpecies }[] {
  const byId = new Map(index.map((s) => [s.id, s]))
  const phrases = new Map<string, MentionSpecies>()
  const add = (phrase: string, species: MentionSpecies) => {
    const key = phrase.trim().toLowerCase()
    if (key.length < 3) return
    if (!phrases.has(key)) phrases.set(key, species)
  }
  for (const species of index) {
    add(species.name, species)
    if (species.common_name) {
      add(species.common_name, species)
      for (const plural of plurals(species.common_name)) add(plural, species)
    }
  }
  for (const [alias, id] of Object.entries(ALIASES)) {
    const species = resolveAlias(byId, id)
    if (species) add(alias, species)
  }
  return [...phrases.entries()]
    .map(([phrase, species]) => ({ phrase, species }))
    .sort((a, b) => b.phrase.length - a.phrase.length)
}

export type TextPart = { text: string; species?: MentionSpecies }

export function splitMentions(text: string, index: MentionSpecies[]): TextPart[] {
  const patterns = mentionPatterns(index)
  if (!patterns.length) return [{ text }]
  const source = patterns
    .map(({ phrase }) => phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  const re = new RegExp(`\\b(${source})\\b`, 'gi')
  const lookup = new Map(patterns.map((p) => [p.phrase, p.species]))
  const parts: TextPart[] = []
  let last = 0
  let match: RegExpExecArray | null
  while ((match = re.exec(text))) {
    if (match.index > last) parts.push({ text: text.slice(last, match.index) })
    const hit = match[0]
    const species = lookup.get(hit.toLowerCase())
    parts.push(species ? { text: hit, species } : { text: hit })
    last = match.index + hit.length
  }
  if (last < text.length) parts.push({ text: text.slice(last) })
  return parts.length ? parts : [{ text }]
}
