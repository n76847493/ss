"""Core types for the visual novel engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Line:
    """A single line of dialogue or narration."""
    speaker: Optional[str]
    text: str

    def render(self) -> str:
        if self.speaker is None:
            return f"<i>{self.text}</i>"
        if self.speaker == "MC":
            return f"<b>Артём:</b> {self.text}"
        return f"<b>{self.speaker}:</b> {self.text}"


@dataclass
class Choice:
    """A single choice option."""
    text: str
    target: str
    effects: dict = field(default_factory=dict)


@dataclass
class ChoiceBlock:
    """A block of choices presented to the player."""
    prompt: Optional[str]
    options: list[Choice]


@dataclass
class Scene:
    """A scene consists of an ordered list of items: lines or choice blocks.

    The last item can be a ChoiceBlock (which terminates the scene), or the
    scene's `next_scene` will be used to continue.
    """
    scene_id: str
    title: str
    items: list
    next_scene: Optional[str] = None
    on_enter: Optional[Callable] = None
