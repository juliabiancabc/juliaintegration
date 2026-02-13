"""
AchievementRepository for SQLite CRUD and achievement_badges link table.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from models.achievement import Achievement
from models.badge import Badge


class AchievementRepository:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, achievement: Achievement, badge_ids: Optional[List[int]] = None) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO achievements (title, description, rule_type, rule_value, active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    achievement.title,
                    achievement.description or "",
                    achievement.rule_type,
                    achievement.rule_value,
                    1 if achievement.active else 0,
                    achievement.created_at,
                ),
            )
            aid = cursor.lastrowid
            for bid in badge_ids or achievement.badge_ids or []:
                cursor.execute(
                    "INSERT INTO achievement_badges (achievement_id, badge_id) VALUES (?, ?)",
                    (aid, bid),
                )
            conn.commit()
            return aid
        finally:
            conn.close()

    def find_by_id(self, achievement_id: int, load_badges: bool = True) -> Optional[Achievement]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM achievements WHERE id = ?", (achievement_id,))
            row = cursor.fetchone()
            if not row:
                return None
            a = Achievement.from_dict(dict(row))
            if load_badges:
                cursor.execute(
                    "SELECT badge_id FROM achievement_badges WHERE achievement_id = ?",
                    (achievement_id,),
                )
                a.badge_ids = [r["badge_id"] for r in cursor.fetchall()]
            return a
        finally:
            conn.close()

    def find_all_active(self, load_badges: bool = True) -> List[Achievement]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM achievements WHERE active = 1 ORDER BY id ASC")
            rows = cursor.fetchall()
            out = []
            for row in rows:
                a = Achievement.from_dict(dict(row))
                if load_badges:
                    cursor.execute(
                        "SELECT badge_id FROM achievement_badges WHERE achievement_id = ?",
                        (a.id,),
                    )
                    a.badge_ids = [r["badge_id"] for r in cursor.fetchall()]
                out.append(a)
            return out
        finally:
            conn.close()

    def find_all(self, load_badges: bool = True) -> List[Achievement]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM achievements ORDER BY id ASC")
            rows = cursor.fetchall()
            out = []
            for row in rows:
                a = Achievement.from_dict(dict(row))
                a.active = bool(row["active"])
                if load_badges:
                    cursor.execute(
                        "SELECT badge_id FROM achievement_badges WHERE achievement_id = ?",
                        (a.id,),
                    )
                    a.badge_ids = [r["badge_id"] for r in cursor.fetchall()]
                out.append(a)
            return out
        finally:
            conn.close()

    def update(self, achievement: Achievement, badge_ids: Optional[List[int]] = None) -> bool:
        if not achievement.id:
            return False
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE achievements SET title = ?, description = ?, rule_type = ?, rule_value = ?, active = ?, created_at = ?
                   WHERE id = ?""",
                (
                    achievement.title,
                    achievement.description or "",
                    achievement.rule_type,
                    achievement.rule_value,
                    1 if achievement.active else 0,
                    achievement.created_at,
                    achievement.id,
                ),
            )
            cursor.execute("DELETE FROM achievement_badges WHERE achievement_id = ?", (achievement.id,))
            for bid in badge_ids if badge_ids is not None else achievement.badge_ids or []:
                cursor.execute(
                    "INSERT INTO achievement_badges (achievement_id, badge_id) VALUES (?, ?)",
                    (achievement.id, bid),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete(self, achievement_id: int) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM achievement_badges WHERE achievement_id = ?", (achievement_id,))
            cursor.execute("DELETE FROM achievements WHERE id = ?", (achievement_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
