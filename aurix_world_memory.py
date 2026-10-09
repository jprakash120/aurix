"""
AURIX Episodic World Memory
===========================

Stores events rather than only chatbot text.

Examples:
- conversation
- explicit user memory
- visual observation
- scene change
- feedback
- local action

SQLite is used because it is:
- local
- persistent
- portable
- queryable
- built into Python
"""

import json
import re
import sqlite3

from datetime import datetime


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "in",
    "on",
    "at",
    "to",
    "of",
    "with",
    "this",
    "that",
    "there",
    "it",
    "i",
    "observe",
    "see",
    "appears",
    "visible",
}


def tokenize_scene(text):

    words = re.findall(
        r"\b[a-zA-Z0-9_-]+\b",
        (
            text
            or ""
        ).lower(),
    )

    return {
        word
        for word in words
        if (
            word not in STOPWORDS
            and len(
                word
            ) > 2
        )
    }


def scene_novelty(
    previous,
    current,
):

    if not previous:
        return 0.0

    old_tokens = tokenize_scene(
        previous
    )

    new_tokens = tokenize_scene(
        current
    )

    if (
        not old_tokens
        or not new_tokens
    ):
        return 1.0

    intersection = len(
        old_tokens
        & new_tokens
    )

    union = len(
        old_tokens
        | new_tokens
    )

    similarity = (
        intersection
        / union
        if union
        else 0.0
    )

    return round(
        1.0 - similarity,
        4,
    )


class EpisodicMemory:

    def __init__(
        self,
        db_path="aurix_world.db",
    ):

        self.db_path = db_path

        self._initialize()

    def _connect(self):

        return sqlite3.connect(
            self.db_path
        )

    def _initialize(self):

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    modality TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT,
                    significance REAL NOT NULL DEFAULT 0.5
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_episodes_timestamp
                ON episodes(timestamp)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_episodes_event_type
                ON episodes(event_type)
                """
            )

    def add_episode(
        self,
        modality,
        event_type,
        summary,
        payload=None,
        significance=0.5,
    ):

        timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

        payload_json = json.dumps(
            payload or {},
            ensure_ascii=False,
        )

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO episodes
                (
                    timestamp,
                    modality,
                    event_type,
                    summary,
                    payload,
                    significance
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    modality,
                    event_type,
                    summary,
                    payload_json,
                    float(
                        significance
                    ),
                ),
            )

            return cursor.lastrowid

    def latest(
        self,
        modality=None,
        event_type=None,
    ):

        clauses = []
        values = []

        if modality:

            clauses.append(
                "modality = ?"
            )

            values.append(
                modality
            )

        if event_type:

            clauses.append(
                "event_type = ?"
            )

            values.append(
                event_type
            )

        where = (
            " WHERE "
            + " AND ".join(
                clauses
            )
            if clauses
            else ""
        )

        query = (
            """
            SELECT
                id,
                timestamp,
                modality,
                event_type,
                summary,
                payload,
                significance
            FROM episodes
            """
            + where
            + """
            ORDER BY id DESC
            LIMIT 1
            """
        )

        with self._connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            row = connection.execute(
                query,
                values,
            ).fetchone()

        return (
            dict(
                row
            )
            if row
            else None
        )

    def recent(
        self,
        limit=10,
        modality=None,
        event_type=None,
    ):

        limit = max(
            1,
            min(
                int(
                    limit
                ),
                100,
            ),
        )

        clauses = []
        values = []

        if modality:

            clauses.append(
                "modality = ?"
            )

            values.append(
                modality
            )

        if event_type:

            clauses.append(
                "event_type = ?"
            )

            values.append(
                event_type
            )

        where = (
            " WHERE "
            + " AND ".join(
                clauses
            )
            if clauses
            else ""
        )

        query = (
            """
            SELECT
                id,
                timestamp,
                modality,
                event_type,
                summary,
                payload,
                significance
            FROM episodes
            """
            + where
            + """
            ORDER BY id DESC
            LIMIT ?
            """
        )

        values.append(
            limit
        )

        with self._connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            rows = connection.execute(
                query,
                values,
            ).fetchall()

        return [
            dict(
                row
            )
            for row in rows
        ]

    def search(
        self,
        text,
        limit=10,
    ):

        text = (
            text
            or ""
        ).strip()

        if not text:
            return []

        pattern = (
            "%"
            + text
            + "%"
        )

        with self._connect() as connection:

            connection.row_factory = (
                sqlite3.Row
            )

            rows = connection.execute(
                """
                SELECT
                    id,
                    timestamp,
                    modality,
                    event_type,
                    summary,
                    payload,
                    significance
                FROM episodes
                WHERE summary LIKE ?
                   OR payload LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    pattern,
                    pattern,
                    int(
                        limit
                    ),
                ),
            ).fetchall()

        return [
            dict(
                row
            )
            for row in rows
        ]

    def count(self):

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM episodes
                """
            ).fetchone()

        return int(
            row[0]
        )

    # -----------------------------------------------------------
    # VISION MEMORY
    # -----------------------------------------------------------

    def record_vision_observation(
        self,
        observation,
        provider=None,
        model=None,
        threshold=0.45,
    ):

        previous = self.latest(
            modality="vision",
            event_type="vision_observation",
        )

        previous_text = (
            previous["summary"]
            if previous
            else ""
        )

        novelty = scene_novelty(
            previous_text,
            observation,
        )

        self.add_episode(
            modality="vision",
            event_type="vision_observation",
            summary=observation,
            payload={
                "provider": provider,
                "model": model,
                "novelty": novelty,
            },
            significance=max(
                0.3,
                novelty,
            ),
        )

        changed = (
            previous is not None
            and novelty >= threshold
        )

        if changed:

            self.add_episode(
                modality="vision",
                event_type="scene_change",
                summary=(
                    "A significant visual scene change was recorded."
                ),
                payload={
                    "previous": previous_text,
                    "current": observation,
                    "novelty": novelty,
                },
                significance=novelty,
            )

        return {
            "novelty": novelty,
            "changed": changed,
            "previous": previous_text,
            "current": observation,
        }

    # -----------------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------------

    @staticmethod
    def format_episode(
        episode
    ):

        if not episode:
            return ""

        return (
            f"[{episode['timestamp']}] "
            f"{episode['event_type']}: "
            f"{episode['summary']}"
        )