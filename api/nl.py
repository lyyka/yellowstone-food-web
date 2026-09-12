from __future__ import annotations

import re
from dataclasses import dataclass

REMOVE_RE = re.compile(
    r"(?:what if (?:we |i )?)?(?:remove|extinct|wipe out|delete|take out)\s+(?:the\s+)?(.+?)[?.!]*$",
    re.I,
)
PREDATORS_RE = re.compile(r"(?:who (?:eats|preys on|hunts)|predators? of)\s+(?:the\s+)?(.+?)[?.!]*$", re.I)
PREY_RE = re.compile(r"(?:what does|what do|diet of|who does)\s+(?:a |an |the )?(.+?)\s+(?:eat|prey on|hunt)[?.!]*$", re.I)
FIND_RE = re.compile(r"(?:find|show|select|about)\s+(?:the\s+)?(.+?)[?.!]*$", re.I)


@dataclass
class ParsedQuery:
    intent: str
    taxon_hint: str
    raw: str


def parse_query(text: str) -> ParsedQuery:
    raw = text.strip()
    if not raw:
        return ParsedQuery(intent="unknown", taxon_hint="", raw=raw)

    if m := REMOVE_RE.search(raw):
        return ParsedQuery(intent="remove", taxon_hint=_clean(m.group(1)), raw=raw)
    if m := PREDATORS_RE.search(raw):
        return ParsedQuery(intent="predators_of", taxon_hint=_clean(m.group(1)), raw=raw)
    if m := PREY_RE.search(raw):
        return ParsedQuery(intent="prey_of", taxon_hint=_clean(m.group(1)), raw=raw)
    if m := FIND_RE.search(raw):
        return ParsedQuery(intent="find", taxon_hint=_clean(m.group(1)), raw=raw)
    return ParsedQuery(intent="find", taxon_hint=_clean(raw), raw=raw)


def _clean(hint: str) -> str:
    hint = hint.strip().strip("?.!")
    hint = re.sub(r"^(the|a|an)\s+", "", hint, flags=re.I)
    return hint
