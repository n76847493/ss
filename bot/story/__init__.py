"""Story modules. Importing this package registers all scenes."""
from __future__ import annotations

import importlib

_MODULES = [
    "bot.story.intro",
    "bot.story.day1",
    "bot.story.day2",
    "bot.story.day3",
    "bot.story.day4",
    "bot.story.day5",
    "bot.story.routes.lena",
    "bot.story.routes.katya",
    "bot.story.routes.anna",
    "bot.story.routes.yulia",
    "bot.story.endings",
]


def load_all() -> None:
    """Import every story module so scenes get registered.

    Modules that don't exist yet are silently skipped — useful while content
    is being added incrementally.
    """
    for mod_name in _MODULES:
        try:
            importlib.import_module(mod_name)
        except ModuleNotFoundError as e:
            # Only swallow errors about THIS module being missing.
            if e.name == mod_name:
                continue
            raise
