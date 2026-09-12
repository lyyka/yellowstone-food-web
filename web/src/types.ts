export type SpeciesNode = {
  id: string
  name: string
  common_name: string | null
  rank: string
  in_region: boolean
  kingdom: string | null
  trophic_hint: string | null
  observation_count: number
  photo_url: string | null
  wikipedia_url: string | null
  path?: string | null
}

export type CatalogSpecies = SpeciesNode & {
  prey_count: number
  predator_count: number
  blurb: string
}

export type Neighbor = SpeciesNode & {
  n_records: number
  relation: string
}

export type SpeciesEdge = {
  source: string
  target: string
  type: string
  n_records: number
}

export type Dossier = {
  species: SpeciesNode
  eats: Neighbor[]
  eaten_by: Neighbor[]
  blurb: string
  graph: { nodes: SpeciesNode[]; edges: SpeciesEdge[] }
}

export type MentionSpecies = {
  id: string
  name: string
  common_name: string | null
  kingdom: string | null
  trophic_hint: string | null
  blurb: string
  photo_url: string | null
  prey_count?: number
  predator_count?: number
  observation_count?: number
}
export type LedgerSpecies = SpeciesNode & {
  prey_count: number
  predator_count: number
  eats: string[]
}

export type CatalogPayload = {
  region: string
  disclaimer: string
  species: CatalogSpecies[]
}

export type GraphPayload = {
  meta: {
    region: string
    disclaimer: string
    sources: string[]
  }
  nodes: SpeciesNode[]
  edges: SpeciesEdge[]
}

export type Effect = {
  node_id: string
  delta_sign: number
  depth: number
  strength: number
  reason: string
  common_name: string | null
  name: string
  kingdom: string | null
}

export type StoryCast = { id: string; label: string }

export type Postcard = {
  title: string
  caption: string
  image_url: string | null
  photos: string[]
  cast: StoryCast[]
}

export type ScenarioResult = {
  prompt: string
  plan: {
    action: string
    fraction: number | null
    guild: string | null
    rationale: string
  }
  removed: SpeciesNode[]
  released: SpeciesNode[]
  pressured: SpeciesNode[]
  story: string[]
  template_story: string[]
  llm: boolean
  lesson: { title: string; blurb: string }
  postcard?: Postcard
}
export type QueryResult = {
  intent?: string
  focus?: SpeciesNode
  removed?: SpeciesNode
  effects: Effect[]
  story: string[]
  template_story?: string[]
  lesson?: { title: string; blurb: string }
  llm?: boolean
  highlight_node_ids: string[]
  highlight_edge_keys: string[]
}
