"""
UserProgressRepository: user stats (from stories/comments), user_badges, user_achievements,
and activity dates for streak (stub).
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from models.badge import Badge, UserBadge
from models.achievement import Achievement, UserAchievement


class UserProgressRepository:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_stats(self, user_id: Optional[int]) -> Dict[str, int]:
        """Compute stories_created_total, comments_written_total, likes_received_total, shares_received_total.
        If user_id is None, return zeros. days_active_streak is stubbed as 0.
        """
        if user_id is None:
            return {
                "stories_created_total": 0,
                "comments_written_total": 0,
                "likes_received_total": 0,
                "shares_received_total": 0,
                "days_active_streak": 0,
            }
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Stories count (non-deleted)
            cursor.execute(
                "SELECT COUNT(*) AS c FROM stories WHERE author_id = ? AND is_deleted = 0",
                (user_id,),
            )
            stories_created_total = cursor.fetchone()["c"] or 0

            cursor.execute(
                "SELECT COUNT(*) AS c FROM comments WHERE author_id = ?",
                (user_id,),
            )
            comments_written_total = cursor.fetchone()["c"] or 0

            cursor.execute(
                "SELECT COALESCE(SUM(likes_count), 0) AS s FROM stories WHERE author_id = ? AND is_deleted = 0",
                (user_id,),
            )
            likes_received_total = cursor.fetchone()["s"] or 0

            cursor.execute(
                "SELECT COALESCE(SUM(shares_count), 0) AS s FROM stories WHERE author_id = ? AND is_deleted = 0",
                (user_id,),
            )
            shares_received_total = cursor.fetchone()["s"] or 0

            # Stub: days_active_streak (optional implementation)
            days_active_streak = 0

            return {
                "stories_created_total": stories_created_total,
                "comments_written_total": comments_written_total,
                "likes_received_total": likes_received_total,
                "shares_received_total": shares_received_total,
                "days_active_streak": days_active_streak,
            }
        finally:
            conn.close()

    def has_achievement(self, user_id: int, achievement_id: int) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                (user_id, achievement_id),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def has_badge(self, user_id: int, badge_id: int) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_badges WHERE user_id = ? AND badge_id = ?",
                (user_id, badge_id),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def award_achievement(self, user_id: int, achievement_id: int) -> bool:
        """Insert user_achievement. Returns True if inserted, False if already had (unique)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, earned_at)
                   VALUES (?, ?, ?)""",
                (user_id, achievement_id, datetime.now().isoformat()),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def award_badge(self, user_id: int, badge_id: int) -> bool:
        """Insert user_badge. Returns True if inserted, False if already had (unique)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO user_badges (user_id, badge_id, earned_at)
                   VALUES (?, ?, ?)""",
                (user_id, badge_id, datetime.now().isoformat()),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_user_badges(
        self,
        user_id: int,
        sort_by: str = "newest",
    ) -> List[UserBadge]:
        """Sort: newest, rarity (count ascending = rarest first), alphabetical (by badge title)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if sort_by == "rarity":
                cursor.execute(
                    """SELECT ub.id, ub.user_id, ub.badge_id, ub.earned_at, b.title, b.description, b.icon_url, b.sort_order
                       FROM user_badges ub
                       JOIN badges b ON b.id = ub.badge_id
                       WHERE ub.user_id = ?
                       ORDER BY (SELECT COUNT(*) FROM user_badges ub2 WHERE ub2.badge_id = ub.badge_id) ASC, ub.earned_at DESC""",
                    (user_id,),
                )
            elif sort_by == "alphabetical":
                cursor.execute(
                    """SELECT ub.id, ub.user_id, ub.badge_id, ub.earned_at, b.title, b.description, b.icon_url, b.sort_order
                       FROM user_badges ub
                       JOIN badges b ON b.id = ub.badge_id
                       WHERE ub.user_id = ?
                       ORDER BY b.title ASC, ub.earned_at DESC""",
                    (user_id,),
                )
            else:
                cursor.execute(
                    """SELECT ub.id, ub.user_id, ub.badge_id, ub.earned_at, b.title, b.description, b.icon_url, b.sort_order
                       FROM user_badges ub
                       JOIN badges b ON b.id = ub.badge_id
                       WHERE ub.user_id = ?
                       ORDER BY ub.earned_at DESC""",
                    (user_id,),
                )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                r = dict(row)
                badge = Badge(
                    id=r["badge_id"],
                    title=r["title"],
                    description=r.get("description"),
                    icon_url=r.get("icon_url"),
                    sort_order=r.get("sort_order", 0),
                )
                result.append(
                    UserBadge.from_dict(
                        {"id": r["id"], "user_id": r["user_id"], "badge_id": r["badge_id"], "earned_at": r["earned_at"]},
                        badge=badge,
                    )
                )
            return result
        finally:
            conn.close()

    def get_user_achievements(self, user_id: int, sort_by: str = "newest") -> List[UserAchievement]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ua.*, a.title, a.description, a.rule_type, a.rule_value
                   FROM user_achievements ua
                   JOIN achievements a ON a.id = ua.achievement_id
                   WHERE ua.user_id = ?
                   ORDER BY ua.earned_at DESC""",
                (user_id,),
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                r = dict(row)
                ach = Achievement(
                    id=r["achievement_id"],
                    title=r["title"],
                    description=r.get("description"),
                    rule_type=r["rule_type"],
                    rule_value=r["rule_value"],
                )
                result.append(
                    UserAchievement.from_dict(
                        {
                            "id": r["id"],
                            "user_id": r["user_id"],
                            "achievement_id": r["achievement_id"],
                            "earned_at": r["earned_at"],
                        },
                        achievement=ach,
                    )
                )
            return result
        finally:
            conn.close()

    def record_activity_date(self, user_id: int, activity_date: Optional[str] = None) -> None:
        """Stub: record a day as active for streak. activity_date = YYYY-MM-DD or today."""
        if user_id is None:
            return
        d = activity_date or datetime.now().strftime("%Y-%m-%d")
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO user_activity_dates (user_id, activity_date) VALUES (?, ?)",
                (user_id, d),
            )
            conn.commit()
        finally:
            conn.close()
