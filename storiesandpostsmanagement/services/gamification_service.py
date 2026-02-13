"""
GamificationService: evaluates achievement rules and awards badges/achievements.
Called after story created, like/unlike, share, comment added.
"""
import os
import sys
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ACHIEVEMENT_RULE_TYPES
from models.badge import Badge, UserBadge
from models.achievement import Achievement, UserAchievement
from repositories.achievement_repository import AchievementRepository
from repositories.badge_repository import BadgeRepository
from repositories.user_progress_repository import UserProgressRepository


class GamificationService:
    """
    Evaluates achievement conditions for a user and awards achievements/badges.
    Returns newly earned badges for "newly earned" UX.
    """

    def __init__(
        self,
        achievement_repo: Optional[AchievementRepository] = None,
        badge_repo: Optional[BadgeRepository] = None,
        user_progress_repo: Optional[UserProgressRepository] = None,
    ):
        self.achievement_repo = achievement_repo or AchievementRepository()
        self.badge_repo = badge_repo or BadgeRepository()
        self.user_progress_repo = user_progress_repo or UserProgressRepository()

    def evaluate_and_award(self, user_id: Optional[int]) -> List[Dict[str, Any]]:
        """
        Evaluate all active achievements for the user; award any newly completed.
        Returns list of newly earned badge dicts (for "newly earned" display).
        If user_id is None, returns [].
        """
        if user_id is None:
            return []

        stats = self.user_progress_repo.get_user_stats(user_id)
        active_achievements = self.achievement_repo.find_all_active(load_badges=True)
        newly_earned_badges: List[Dict[str, Any]] = []

        for ach in active_achievements:
            if self.user_progress_repo.has_achievement(user_id, ach.id):
                continue
            if not self._rule_satisfied(ach, stats):
                continue
            # Award achievement (unique constraint prevents duplicate)
            if not self.user_progress_repo.award_achievement(user_id, ach.id):
                continue
            # Award each linked badge
            for badge_id in ach.badge_ids:
                if self.user_progress_repo.award_badge(user_id, badge_id):
                    badge = self.badge_repo.find_by_id(badge_id)
                    if badge:
                        newly_earned_badges.append({
                            "badge_id": badge.id,
                            "title": badge.title,
                            "description": badge.description,
                            "icon_url": badge.icon_url,
                        })
        return newly_earned_badges

    def _rule_satisfied(self, achievement: Achievement, stats: Dict[str, int]) -> bool:
        """Check if user's stats satisfy the achievement rule (value >= N)."""
        rule_type = achievement.rule_type
        required = achievement.rule_value
        if rule_type == "stories_created_total":
            return stats.get("stories_created_total", 0) >= required
        if rule_type == "comments_written_total":
            return stats.get("comments_written_total", 0) >= required
        if rule_type == "likes_received_total":
            return stats.get("likes_received_total", 0) >= required
        if rule_type == "shares_received_total":
            return stats.get("shares_received_total", 0) >= required
        if rule_type == "days_active_streak":
            return stats.get("days_active_streak", 0) >= required
        return False

    def get_user_badges(
        self,
        user_id: int,
        sort_by: str = "newest",
    ) -> List[UserBadge]:
        """Sort: newest, rarity, alphabetical."""
        return self.user_progress_repo.get_user_badges(user_id, sort_by=sort_by)

    def get_user_achievements(self, user_id: int, sort_by: str = "newest") -> List[UserAchievement]:
        return self.user_progress_repo.get_user_achievements(user_id, sort_by=sort_by)

    def get_badge_catalog(self, order_by: str = "sort_order") -> List[Badge]:
        return self.badge_repo.find_all(order_by=order_by)

    def record_activity(self, user_id: Optional[int]) -> None:
        """Stub: record today as active for streak calculation."""
        if user_id is not None:
            self.user_progress_repo.record_activity_date(user_id)
