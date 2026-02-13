"""
CommentService class for business logic.
Handles comment operations with validation.
"""
import os
from typing import Optional, List, Dict, Tuple, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.comment import Comment
from repositories.comment_repository import CommentRepository
from services.gamification_service import GamificationService


class CommentService:
    """
    Service class for comment business logic.
    Handles validation and delegates to repository.
    """
    
    def __init__(
        self,
        repository: Optional[CommentRepository] = None,
        gamification_service: Optional[GamificationService] = None,
    ):
        """Initialize service with repository and optional gamification."""
        self.repository = repository or CommentRepository()
        self.gamification_service = gamification_service or GamificationService()
    
    def add_comment(
        self,
        story_id: int,
        author_name: str,
        content: str,
        author_id: Optional[int] = None,
    ) -> Tuple[Optional[Comment], Dict[str, str], List[Dict[str, Any]]]:
        """
        Add a new comment to a story.
        Returns tuple of (created_comment, errors, newly_earned_badges).
        """
        # Create comment object
        comment = Comment(
            story_id=story_id,
            author_name=author_name.strip() if author_name else '',
            content=content.strip() if content else '',
            author_id=author_id,
        )
        
        # Validate
        errors = comment.validate()
        if errors:
            return None, errors, []
        
        # Save to database
        comment_id = self.repository.create(comment)
        comment.id = comment_id
        
        # Gamification: evaluate and award for comment author
        self.gamification_service.record_activity(author_id)
        newly_earned = self.gamification_service.evaluate_and_award(author_id) if author_id is not None else []
        
        return comment, {}, newly_earned
    
    def get_comments(self, story_id: int) -> List[Comment]:
        """Get all comments for a story."""
        return self.repository.find_by_story_id(story_id)
    
    def delete_comment(self, comment_id: int) -> bool:
        """Delete a comment. Returns True if successful."""
        return self.repository.delete(comment_id)
    
    def get_comment(self, comment_id: int) -> Optional[Comment]:
        """Get a single comment by ID."""
        return self.repository.find_by_id(comment_id)
