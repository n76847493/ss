"""Registry of all scenes in the story."""
from __future__ import annotations

from .types import Scene

_REGISTRY: dict[str, Scene] = {}


def register(scene: Scene) -> Scene:
    if scene.scene_id in _REGISTRY:
        raise ValueError(f"Duplicate scene id: {scene.scene_id}")
    _REGISTRY[scene.scene_id] = scene
    return scene


def get_scene(scene_id: str) -> Scene:
    if scene_id not in _REGISTRY:
        raise KeyError(f"Scene not found: {scene_id}")
    return _REGISTRY[scene_id]


def all_scene_ids() -> list[str]:
    return list(_REGISTRY.keys())


def total_lines() -> int:
    """Count total lines of dialogue across all registered scenes."""
    from .types import Line
    count = 0
    for scene in _REGISTRY.values():
        for item in scene.items:
            if isinstance(item, Line):
                count += 1
    return count
