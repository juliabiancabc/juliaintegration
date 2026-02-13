"""
Badge and UserBadge entity classes.
Badge: collectible icon/title shown on profile.
UserBadge: record of a user earning a badge (with earned_at).
"""
from datetime import datetime
from typing import Optional, Dict, Any


class Badge:
    """
    Entity representing a collectible badge (e.g. "Storyteller", "Top Helper").
    """

    def __init__(
        self,
        title: str,
        id: Optional[int] = None,
        description: Optional[str] = None,
        icon_url: Optional[str] = None,
        sort_order: int = 0,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.description = description or ""
        self.icon_url = icon_url or ""
        self.sort_order = sort_order
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "icon_url": self.icon_url,
            "sort_order": self.sort_order,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Badge":
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            sort_order=data.get("sort_order", 0),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"Badge(id={self.id}, title='{self.title}')"


class UserBadge:
    """
    Record of a user earning a badge (unique per user per badge).
    """

    def __init__(
        self,
        user_id: int,
        badge_id: int,
        earned_at: Optional[str] = None,
        id: Optional[int] = None,
        badge: Optional[Badge] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.badge_id = badge_id
        self.earned_at = earned_at or datetime.now().isoformat()
        self.badge = badge  # optional: populated when joined with badges

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "user_id": self.user_id,
            "badge_id": self.badge_id,
            "earned_at": self.earned_at,
        }
        if self.badge:
            d["badge"] = self.badge.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], badge: Optional[Badge] = None) -> "UserBadge":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            badge_id=data["badge_id"],
            earned_at=data.get("earned_at"),
            badge=badge,
        )

    def __repr__(self) -> str:
        return f"UserBadge(user_id={self.user_id}, badge_id={self.badge_id}, earned_at={self.earned_at})"
