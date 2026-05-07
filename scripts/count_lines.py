"""Count total Line() entries across the story."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.engine.registry import all_scene_ids, get_scene, total_lines  # noqa: E402
from bot.engine.types import ChoiceBlock, Line  # noqa: E402
from bot.story import load_all  # noqa: E402

load_all()

per_scene: dict[str, int] = {}
choice_blocks = 0
total_choices = 0
for sid in all_scene_ids():
    sc = get_scene(sid)
    n_lines = 0
    for it in sc.items:
        if isinstance(it, Line):
            n_lines += 1
        elif isinstance(it, ChoiceBlock):
            choice_blocks += 1
            total_choices += len(it.options)
    per_scene[sid] = n_lines

print(f"Scenes: {len(per_scene)}")
print(f"Choice blocks: {choice_blocks}")
print(f"Total choices: {total_choices}")
print(f"Total dialogue lines: {total_lines()}")
print()
print("Top 10 longest scenes:")
for sid, ln in sorted(per_scene.items(), key=lambda x: -x[1])[:10]:
    print(f"  {sid}: {ln}")
