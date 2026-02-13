"""
Achievement and UserAchievement entity classes.
Achievement: a rule/condition (e.g. "Post 5 stories") that can award one or more badges.
UserAchievement: record of a user earning an achievement (with earned_at).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from .badge import Badge


class Achievement:
    """
    Entity representing an achievement rule (e.g. stories_created_total >= 5).
    """

    def __init__(
        self,
        title: str,
        rule_type: str,
        rule_value: int,
        id: Optional[int] = None,
        description: Optional[str] = None,
        active: bool = True,
        created_at: Optional[str] = None,
        badge_ids: Optional[List[int]] = None,
        badges: Optional[List[Badge]] = None,
    ):
        self.id = id
        self.title = title
        self.description = description or ""
        self.rule_type = rule_type
        self.rule_value = rule_value
        self.active = active
        self.created_at = created_at or datetime.now().isoformat()
        self.badge_ids = badge_ids or []
        self.badges = badges or []

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "rule_type": self.rule_type,
            "rule_value": self.rule_value,
            "active": self.active,
            "created_at": self.created_at,
            "badge_ids": self.badge_ids,
        }
        if self.badges:
            d["badges"] = [b.to_dict() for b in self.badges]
        return d

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        badge_ids: Optional[List[int]] = None,
        badges: Optional[List[Badge]] = None,
    ) -> "Achievement":
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description"),
            rule_type=data.get("rule_type", ""),
            rule_value=data.get("rule_value", 0),
            active=bool(data.get("active", 1)),
            created_at=data.get("created_at"),
            badge_ids=badge_ids or data.get("badge_ids") or [],
            badges=badges or [],
        )

    def __repr__(self) -> str:
        return f"Achievement(id={self.id}, title='{self.title}', rule_type='{self.rule_type}', rule_value={self.rule_value})"


class UserAchievement:
    """
    Record of a user earning an achievement (unique per user per achievement).
    """

    def __init__(
        self,
        user_id: int,
        achievement_id: int,
        earned_at: Optional[str] = None,
        id: Optional[int] = None,
        achievement: Optional[Achievement] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.achievement_id = achievement_id
        self.earned_at = earned_at or datetime.now().isoformat()
        self.achievement = achievement

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "user_id": self.user_id,
            "achievement_id": self.achievement_id,
            "earned_at": self.earned_at,
        }
        if self.achievement:
            d["achievement"] = self.achievement.to_dict()
        return d

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], achievement: Optional[Achievement] = None
    ) -> "UserAchievement":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            achievement_id=data["achievement_id"],
            earned_at=data.get("earned_at"),
            achievement=achievement,
        )

    def __repr__(self) -> str:
        return f"UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id}, earned_at={self.earned_at})"
