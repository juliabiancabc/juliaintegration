"""
Comment entity class with validation methods.
Represents a comment on a story post in the LazarusStories system.
"""
from datetime import datetime
from typing import Optional, Dict, Any


class Comment:
    """
    Entity class representing a comment on a story.
    Contains validation methods for the comment entity.
    """
    
    def __init__(
        self,
        story_id: int,
        author_name: str,
        content: str,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        author_id: Optional[int] = None
    ):
        self.id = id
        self.story_id = story_id
        self.author_name = author_name
        self.author_id = author_id
        self.content = content
        self.created_at = created_at or datetime.now().isoformat()
    
    def validate(self) -> Dict[str, str]:
        """
        Validate the comment data.
        Returns a dictionary of field names to error messages.
        Empty dictionary means validation passed.
        """
        errors = {}
        
        # Validate author_name
        if not self.author_name or not self.author_name.strip():
            errors['author_name'] = "Name is required"
        elif len(self.author_name) > 50:
            errors['author_name'] = "Name must be 50 characters or less"
        
        # Validate content
        if not self.content or not self.content.strip():
            errors['content'] = "Comment is required"
        elif len(self.content) > 1000:
            errors['content'] = "Comment must be 1000 characters or less"
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Comment to a dictionary."""
        return {
            'id': self.id,
            'story_id': self.story_id,
            'author_name': self.author_name,
            'author_id': self.author_id,
            'content': self.content,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """Create a Comment from a dictionary (database row)."""
        return cls(
            id=data.get('id'),
            story_id=data.get('story_id'),
            author_name=data.get('author_name', ''),
            author_id=data.get('author_id'),
            content=data.get('content', ''),
            created_at=data.get('created_at')
        )
    
    def __repr__(self) -> str:
        return f"Comment(id={self.id}, story_id={self.story_id}, author='{self.author_name}')"
