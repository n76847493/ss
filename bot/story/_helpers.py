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
