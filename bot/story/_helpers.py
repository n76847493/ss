"""Tiny helpers to make story files terser."""
from __future__ import annotations

from ..engine.registry import register
from ..engine.types import Choice, ChoiceBlock, Line, Scene


def n(text: str) -> Line:
    """Narration (no speaker)."""
    return Line(speaker=None, text=text)


def mc(text: str) -> Line:
    """Protagonist line."""
    return Line(speaker="MC", text=text)


def s(speaker: str, text: str) -> Line:
    """A line by a named speaker."""
    return Line(speaker=speaker, text=text)


def choice(prompt: str | None, *opts: Choice) -> ChoiceBlock:
    return ChoiceBlock(prompt=prompt, options=list(opts))


def opt(text: str, target: str, **effects) -> Choice:
    return Choice(text=text, target=target, effects=effects)


def scene(scene_id: str, title: str, items: list, next_scene: str | None = None) -> Scene:
    sc = Scene(scene_id=scene_id, title=title, items=items, next_scene=next_scene)
    return register(sc)


def block(text: str) -> list[Line]:
    """Parse a multi-line script into a list of Line objects.

    Conventions per non-empty stripped line:
      - 'N: ...' or '. ...' or no-prefix line starting with '(' or italic context
        becomes narration.
      - 'MC: ...' becomes the protagonist's line.
      - 'Speaker: ...' becomes a line by that named speaker.
      - blank lines are skipped.

    Use triple-quoted strings to fit lots of dialogue in a small amount of source.
    """
    out: list[Line] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # treat hash lines as comments (ignored)
            continue
        if line.startswith("N:"):
            out.append(n(line[2:].strip()))
            continue
        if line.startswith(".") and not line.startswith(".."):
            out.append(n(line[1:].strip()))
            continue
        if line.startswith("MC:"):
            out.append(mc(line[3:].strip()))
            continue
        # Speaker:text form
        if ":" in line:
            speaker, _, body = line.partition(":")
            speaker = speaker.strip()
            body = body.strip()
            if speaker and body:
                out.append(s(speaker, body))
                continue
        # Fallback: treat as narration
        out.append(n(line))
    return out
