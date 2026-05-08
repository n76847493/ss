"""Scene runner: drives progression through scenes."""
from __future__ import annotations

from dataclasses import dataclass

from .registry import get_scene
from .types import ChoiceBlock, Line, Scene


# Number of dialogue lines to send in one Telegram message.
LINES_PER_MESSAGE = 4


@dataclass
class RenderResult:
    text: str
    choices: list | None  # list[Choice] or None
    is_end: bool
    next_scene_id: str | None
    next_index: int


def render_step(scene_id: str, index: int) -> RenderResult:
    """Render the next chunk from the given scene starting at `index`.

    Returns text to display, choices (if reached a choice block), or None
    (continue), plus updated next_scene_id and next_index for the player state.
    """
    scene = get_scene(scene_id)
    chunk_lines: list[str] = []
    i = index

    # Add scene title if at start
    if index == 0:
        chunk_lines.append(f"<u><b>{scene.title}</b></u>\n")

    while i < len(scene.items):
        item = scene.items[i]
        if isinstance(item, Line):
            chunk_lines.append(item.render())
            i += 1
            # If we have enough lines to display, return chunk
            if len([x for x in chunk_lines if "<b>" in x or "<i>" in x]) >= LINES_PER_MESSAGE:
                return RenderResult(
                    text="\n\n".join(chunk_lines),
                    choices=None,
                    is_end=False,
                    next_scene_id=scene_id,
                    next_index=i,
                )
        elif isinstance(item, ChoiceBlock):
            if item.prompt:
                chunk_lines.append(f"<i>{item.prompt}</i>")
            return RenderResult(
                text="\n\n".join(chunk_lines) if chunk_lines else "",
                choices=item.options,
                is_end=False,
                next_scene_id=scene_id,
                next_index=i,  # stays here until choice made
            )
        else:
            i += 1

    # Reached end of scene's items
    if scene.next_scene is None:
        return RenderResult(
            text="\n\n".join(chunk_lines) if chunk_lines else "",
            choices=None,
            is_end=True,
            next_scene_id=None,
            next_index=0,
        )

    return RenderResult(
        text="\n\n".join(chunk_lines) if chunk_lines else "",
        choices=None,
        is_end=False,
        next_scene_id=scene.next_scene,
        next_index=0,
    )


def apply_choice(
    scene_id: str, index: int, choice_idx: int, variables: dict
) -> tuple[str, int, dict]:
    """Apply choice effects and return (next_scene_id, next_index, updated_vars)."""
    scene = get_scene(scene_id)
    item = scene.items[index]
    assert isinstance(item, ChoiceBlock)
    choice = item.options[choice_idx]
    new_vars = dict(variables)
    for k, v in choice.effects.items():
        if isinstance(v, int):
            new_vars[k] = new_vars.get(k, 0) + v
        else:
            new_vars[k] = v
    return choice.target, 0, new_vars
