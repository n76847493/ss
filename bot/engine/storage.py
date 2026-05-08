"""SQLite save system."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "saves.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                current_scene TEXT NOT NULL,
                current_index INTEGER NOT NULL DEFAULT 0,
                variables TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS saves (
                user_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                current_scene TEXT NOT NULL,
                current_index INTEGER NOT NULL,
                variables TEXT NOT NULL,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, slot)
            );
            """
        )


def get_player(user_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "user_id": row["user_id"],
            "current_scene": row["current_scene"],
            "current_index": row["current_index"],
            "variables": json.loads(row["variables"]),
        }


def upsert_player(
    user_id: int, current_scene: str, current_index: int, variables: dict
) -> None:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO players (user_id, current_scene, current_index, variables, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_scene = excluded.current_scene,
                current_index = excluded.current_index,
                variables = excluded.variables,
                updated_at = excluded.updated_at
            """,
            (user_id, current_scene, current_index, json.dumps(variables), now),
        )


def reset_player(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM players WHERE user_id = ?", (user_id,))


def save_slot(user_id: int, slot: int, label: str, player: dict) -> None:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO saves (user_id, slot, current_scene, current_index, variables, label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, slot) DO UPDATE SET
                current_scene = excluded.current_scene,
                current_index = excluded.current_index,
                variables = excluded.variables,
                label = excluded.label,
                created_at = excluded.created_at
            """,
            (
                user_id,
                slot,
                player["current_scene"],
                player["current_index"],
                json.dumps(player["variables"]),
                label,
                now,
            ),
        )


def list_saves(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT slot, label, created_at FROM saves WHERE user_id = ? ORDER BY slot",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def load_slot(user_id: int, slot: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM saves WHERE user_id = ? AND slot = ?", (user_id, slot)
        ).fetchone()
        if row is None:
            return None
        return {
            "current_scene": row["current_scene"],
            "current_index": row["current_index"],
            "variables": json.loads(row["variables"]),
        }


def delete_slot(user_id: int, slot: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM saves WHERE user_id = ? AND slot = ?", (user_id, slot))
