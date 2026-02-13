"""
BadgeRepository for SQLite CRUD operations on badges.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from models.badge import Badge


class BadgeRepository:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, badge: Badge) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO badges (title, description, icon_url, sort_order, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    badge.title,
                    badge.description or "",
                    badge.icon_url or "",
                    badge.sort_order,
                    badge.created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def find_by_id(self, badge_id: int) -> Optional[Badge]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM badges WHERE id = ?", (badge_id,))
            row = cursor.fetchone()
            return Badge.from_dict(dict(row)) if row else None
        finally:
            conn.close()

    def find_all(self, order_by: str = "sort_order") -> List[Badge]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if order_by == "title":
                cursor.execute("SELECT * FROM badges ORDER BY title ASC")
            elif order_by == "newest":
                cursor.execute("SELECT * FROM badges ORDER BY created_at DESC")
            else:
                cursor.execute("SELECT * FROM badges ORDER BY sort_order ASC, id ASC")
            rows = cursor.fetchall()
            return [Badge.from_dict(dict(r)) for r in rows]
        finally:
            conn.close()

    def update(self, badge: Badge) -> bool:
        if not badge.id:
            return False
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE badges SET title = ?, description = ?, icon_url = ?, sort_order = ?, created_at = ?
                   WHERE id = ?""",
                (
                    badge.title,
                    badge.description or "",
                    badge.icon_url or "",
                    badge.sort_order,
                    badge.created_at,
                    badge.id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete(self, badge_id: int) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM badges WHERE id = ?", (badge_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
