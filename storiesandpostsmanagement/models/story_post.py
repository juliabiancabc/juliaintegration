"""
StoryPost entity class with validation methods.
Represents a story/memory post in the LazarusStories system.
"""
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VALID_CATEGORIES, VALID_PRIVACY_OPTIONS, EDIT_LOCK_HOURS


class StoryPost:
    """
    Entity class representing a story post.
    Contains validation methods and business logic for the post entity.
    """
    
    def __init__(
        self,
        caption: str,
        description: str,
        category: str,
        privacy: str,
        id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        event_title: Optional[str] = None,
        allowed_groups: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None,
        media_paths: Optional[List[str]] = None,
        likes_count: int = 0,
        comments_count: int = 0,
        shares_count: int = 0,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        is_deleted: bool = False,
        deleted_at: Optional[str] = None,
        author_id: Optional[int] = None
    ):
        self.id = id
        self.author_id = author_id
        self.caption = caption
        self.description = description
        self.tags = tags or []
        self.event_title = event_title
        self.category = category
        self.privacy = privacy
        self.allowed_groups = allowed_groups or []
        self.scheduled_at = scheduled_at
        self.media_paths = media_paths or []
        self.likes_count = likes_count
        self.comments_count = comments_count
        self.shares_count = shares_count
        
        now = datetime.now().isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.is_deleted = is_deleted
        self.deleted_at = deleted_at
    
    def validate(self) -> Dict[str, str]:
        """
        Validate the story post data.
        Returns a dictionary of field names to error messages.
        Empty dictionary means validation passed.
        """
        errors = {}
        
        # Validate caption
        caption_error = self._validate_caption()
        if caption_error:
            errors['caption'] = caption_error
        
        # Validate description
        description_error = self._validate_description()
        if description_error:
            errors['description'] = description_error
        
        # Validate tags
        tags_error = self._validate_tags()
        if tags_error:
            errors['tags'] = tags_error
        
        # Validate category
        category_error = self._validate_category()
        if category_error:
            errors['category'] = category_error
        
        # Validate privacy
        privacy_error = self._validate_privacy()
        if privacy_error:
            errors['privacy'] = privacy_error
        
        # Validate allowed_groups if privacy is Specific Groups
        if self.privacy == 'Specific Groups':
            groups_error = self._validate_allowed_groups()
            if groups_error:
                errors['allowed_groups'] = groups_error
        
        return errors
    
    def _validate_caption(self) -> Optional[str]:
        """Validate caption field."""
        if not self.caption or not self.caption.strip():
            return "Caption is required"
        if len(self.caption) > 120:
            return "Caption must be 120 characters or less"
        return None
    
    def _validate_description(self) -> Optional[str]:
        """Validate description field."""
        if not self.description or not self.description.strip():
            return "Description is required"
        if len(self.description) < 20:
            return "Description must be at least 20 characters"
        return None
    
    def _validate_tags(self) -> Optional[str]:
        """Validate tags field."""
        if len(self.tags) > 10:
            return "Maximum 10 tags allowed"
        
        # Pattern: alphanumeric and underscore only
        tag_pattern = re.compile(r'^[a-zA-Z0-9_]+$')
        for tag in self.tags:
            # Strip leading # if present
            clean_tag = tag.lstrip('#')
            if not tag_pattern.match(clean_tag):
                return "Tags can only contain letters, numbers, and underscores"
        
        return None
    
    def _validate_category(self) -> Optional[str]:
        """Validate category field."""
        if not self.category:
            return "Category is required"
        if self.category not in VALID_CATEGORIES:
            return "Please select a valid category"
        return None
    
    def _validate_privacy(self) -> Optional[str]:
        """Validate privacy field."""
        if not self.privacy:
            return "Privacy setting is required"
        if self.privacy not in VALID_PRIVACY_OPTIONS:
            return "Please select a valid privacy setting"
        return None
    
    def _validate_allowed_groups(self) -> Optional[str]:
        """Validate allowed_groups when privacy is Specific Groups."""
        if not self.allowed_groups or len(self.allowed_groups) == 0:
            return "Please specify at least one group"
        return None
    
    def is_editable(self) -> bool:
        """
        Check if caption/description can still be edited.
        Returns True if within 24 hours of creation.
        """
        created = datetime.fromisoformat(self.created_at)
        now = datetime.now()
        hours_since_creation = (now - created).total_seconds() / 3600
        return hours_since_creation < EDIT_LOCK_HOURS
    
    def can_be_restored(self) -> bool:
        """
        Check if the post can be restored from soft delete.
        Returns True if deleted within the last 7 days.
        """
        if not self.is_deleted or not self.deleted_at:
            return False
        
        deleted = datetime.fromisoformat(self.deleted_at)
        now = datetime.now()
        days_since_deletion = (now - deleted).days
        return days_since_deletion < 7
    
    def is_published(self) -> bool:
        """
        Check if the post should be published based on scheduled_at.
        Returns True if not scheduled or if scheduled time has passed.
        """
        if not self.scheduled_at:
            return True
        
        scheduled = datetime.fromisoformat(self.scheduled_at)
        return datetime.now() >= scheduled
    
    def clean_tags(self) -> None:
        """Remove leading # from all tags."""
        self.tags = [tag.lstrip('#') for tag in self.tags]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the StoryPost to a dictionary."""
        return {
            'id': self.id,
            'author_id': self.author_id,
            'caption': self.caption,
            'description': self.description,
            'tags': json.dumps(self.tags),
            'event_title': self.event_title,
            'category': self.category,
            'privacy': self.privacy,
            'allowed_groups': json.dumps(self.allowed_groups),
            'scheduled_at': self.scheduled_at,
            'media_paths': json.dumps(self.media_paths),
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'shares_count': self.shares_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_deleted': 1 if self.is_deleted else 0,
            'deleted_at': self.deleted_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryPost':
        """Create a StoryPost from a dictionary (database row)."""
        # Parse JSON fields
        tags = json.loads(data.get('tags') or '[]')
        allowed_groups = json.loads(data.get('allowed_groups') or '[]')
        media_paths = json.loads(data.get('media_paths') or '[]')
        
        return cls(
            id=data.get('id'),
            author_id=data.get('author_id'),
            caption=data.get('caption', ''),
            description=data.get('description', ''),
            tags=tags,
            event_title=data.get('event_title'),
            category=data.get('category', ''),
            privacy=data.get('privacy', ''),
            allowed_groups=allowed_groups,
            scheduled_at=data.get('scheduled_at'),
            media_paths=media_paths,
            likes_count=data.get('likes_count', 0),
            comments_count=data.get('comments_count', 0),
            shares_count=data.get('shares_count', 0),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            is_deleted=bool(data.get('is_deleted', 0)),
            deleted_at=data.get('deleted_at')
        )
    
    def __repr__(self) -> str:
        return f"StoryPost(id={self.id}, caption='{self.caption[:30]}...', category='{self.category}')"
