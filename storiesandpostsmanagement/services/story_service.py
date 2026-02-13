"""
StoryService class for business logic.
Handles story operations with business rules enforcement.
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH,
    VALID_CATEGORIES, VALID_PRIVACY_OPTIONS
)
from models.story_post import StoryPost
from repositories.story_repository import StoryRepository
from services.gamification_service import GamificationService


class StoryService:
    """
    Service class for story business logic.
    Enforces business rules like 24h edit lock, 7-day recovery, etc.
    """
    
    def __init__(
        self,
        repository: Optional[StoryRepository] = None,
        gamification_service: Optional[GamificationService] = None,
    ):
        """Initialize service with repository and optional gamification."""
        self.repository = repository or StoryRepository()
        self.gamification_service = gamification_service or GamificationService()
        self._ensure_upload_folder()
    
    def _ensure_upload_folder(self) -> None:
        """Ensure the upload folder exists."""
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if a file has an allowed extension."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def _is_image(self, filename: str) -> bool:
        """Check if file is an image."""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    def _is_video(self, filename: str) -> bool:
        """Check if file is a video."""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in {'mp4', 'webm', 'mov', 'avi'}
    
    def save_media_files(self, files: List[FileStorage]) -> Tuple[List[str], List[str]]:
        """
        Save uploaded media files with enhanced validation.
        Returns tuple of (saved_paths, errors).
        """
        saved_paths = []
        errors = []

        # Allowed MIME types for validation
        allowed_image_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        allowed_video_types = {'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo'}

        # Magic bytes for image detection (replaces imghdr removed in Python 3.13)
        _image_signatures = {
            b'\xff\xd8\xff': 'jpeg',
            b'\x89PNG\r\n\x1a\n': 'png',
            b'GIF87a': 'gif',
            b'GIF89a': 'gif',
            b'RIFF': 'webp',  # WebP starts with RIFF....WEBP
        }

        def _detect_image_type(f):
            header = f.read(12)
            f.seek(0)
            for sig, fmt in _image_signatures.items():
                if header[:len(sig)] == sig:
                    if fmt == 'webp' and header[8:12] != b'WEBP':
                        continue
                    return fmt
            return None

        for file in files:
            if file and file.filename:
                # Check file extension first
                if not self._allowed_file(file.filename):
                    errors.append(f"Invalid file type: {file.filename}")
                    continue

                # Check file size
                file.seek(0, 2)
                size = file.tell()
                file.seek(0)

                if size > MAX_CONTENT_LENGTH:
                    errors.append(f"File too large: {file.filename} (max 50MB)")
                    continue

                if size == 0:
                    errors.append(f"Empty file: {file.filename}")
                    continue

                # Validate content type from header
                content_type = file.content_type or ''
                if not (content_type in allowed_image_types or content_type in allowed_video_types):
                    errors.append(f"Invalid content type for {file.filename}: {content_type}")
                    continue

                # For images, verify actual content matches declared type
                if content_type in allowed_image_types:
                    file.seek(0)
                    detected_type = _detect_image_type(file)
                    file.seek(0)
                    if detected_type not in ['jpeg', 'png', 'gif', 'webp']:
                        errors.append(f"File content doesn't match image type: {file.filename}")
                        continue
                
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, unique_name)
                
                try:
                    file.save(filepath)
                    # Store relative path for web access
                    saved_paths.append(f"uploads/{unique_name}")
                except Exception as e:
                    errors.append(f"Failed to save {file.filename}: {str(e)}")
        
        return saved_paths, errors
    
    def create_story(
        self,
        caption: str,
        description: str,
        category: str,
        privacy: str,
        tags: Optional[List[str]] = None,
        event_title: Optional[str] = None,
        allowed_groups: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None,
        media_files: Optional[List[FileStorage]] = None,
        current_user_id: Optional[int] = None,
    ) -> Tuple[Optional[StoryPost], Dict[str, str], List[Dict[str, Any]]]:
        """
        Create a new story with validation.
        Returns tuple of (created_story, errors, newly_earned_badges).
        """
        # Clean tags (remove leading #)
        if tags:
            tags = [tag.lstrip('#') for tag in tags if tag.strip()]
        
        # Create story object
        story = StoryPost(
            caption=caption.strip() if caption else '',
            description=description.strip() if description else '',
            category=category,
            privacy=privacy,
            tags=tags or [],
            event_title=event_title,
            allowed_groups=allowed_groups or [],
            scheduled_at=scheduled_at,
            author_id=current_user_id,
        )
        
        # Validate story
        errors = story.validate()
        if errors:
            return None, errors, []
        
        # Save media files if provided
        if media_files:
            saved_paths, file_errors = self.save_media_files(media_files)
            if file_errors:
                errors['media'] = '; '.join(file_errors)
                return None, errors, []
            story.media_paths = saved_paths
        
        # Save to database
        story_id = self.repository.create(story)
        story.id = story_id
        
        # Gamification: evaluate and award for author
        self.gamification_service.record_activity(current_user_id)
        newly_earned = self.gamification_service.evaluate_and_award(current_user_id)
        
        return story, {}, newly_earned
    
    def get_story(self, story_id: int) -> Optional[StoryPost]:
        """Get a story by ID."""
        return self.repository.find_by_id(story_id)
    
    def list_stories(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = 'recent'
    ) -> List[StoryPost]:
        """List stories with optional filters."""
        return self.repository.find_all(
            search=search,
            category=category,
            sort_by=sort_by
        )
    
    def update_story(
        self,
        story_id: int,
        caption: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        privacy: Optional[str] = None,
        tags: Optional[List[str]] = None,
        allowed_groups: Optional[List[str]] = None,
        media_files: Optional[List[FileStorage]] = None
    ) -> Tuple[Optional[StoryPost], Dict[str, str]]:
        """
        Update a story with 24h lock enforcement.
        Returns tuple of (updated_story, errors).
        """
        story = self.repository.find_by_id(story_id)
        if not story:
            return None, {'general': 'Story not found'}
        
        if story.is_deleted:
            return None, {'general': 'Cannot edit a deleted story'}
        
        is_editable = story.is_editable()
        
        # Update fields based on editability
        if is_editable:
            # Can edit caption and description within 24 hours
            if caption is not None:
                story.caption = caption.strip()
            if description is not None:
                story.description = description.strip()
        
        # These can always be updated
        if category is not None:
            story.category = category
        if privacy is not None:
            story.privacy = privacy
        if tags is not None:
            story.tags = [tag.lstrip('#') for tag in tags if tag.strip()]
        if allowed_groups is not None:
            story.allowed_groups = allowed_groups
        
        # Validate updated story
        errors = story.validate()
        if errors:
            return None, errors
        
        # Add new media files if provided
        if media_files:
            saved_paths, file_errors = self.save_media_files(media_files)
            if file_errors:
                errors['media'] = '; '.join(file_errors)
                return None, errors
            story.media_paths.extend(saved_paths)
        
        # Update in database
        success = self.repository.update(story)
        if not success:
            return None, {'general': 'Failed to update story'}
        
        return story, {}
    
    def delete_story(self, story_id: int) -> Tuple[bool, Optional[str]]:
        """
        Soft delete a story.
        Returns tuple of (success, story_title_for_message).
        """
        story = self.repository.find_by_id(story_id)
        if not story:
            return False, None
        
        success = self.repository.soft_delete(story_id)
        return success, story.caption if success else None
    
    def restore_story(self, story_id: int) -> Tuple[bool, str]:
        """
        Restore a soft-deleted story.
        Returns tuple of (success, message).
        """
        story = self.repository.find_by_id(story_id)
        if not story:
            return False, "Story not found"
        
        if not story.is_deleted:
            return False, "Story is not deleted"
        
        if not story.can_be_restored():
            return False, "Story cannot be restored (expired after 7 days)"
        
        success = self.repository.restore(story_id)
        return success, "Story restored successfully" if success else "Failed to restore story"
    
    def list_deleted_stories(self) -> List[StoryPost]:
        """List all recoverable deleted stories."""
        return self.repository.find_deleted()
    
    def purge_expired_stories(self) -> int:
        """Permanently delete expired soft-deleted stories."""
        return self.repository.purge_expired()
    
    def like_story(self, story_id: int) -> Tuple[int, List[Dict[str, Any]]]:
        """Increment likes for a story. Returns (new_count, newly_earned_badges for story owner)."""
        story = self.repository.find_by_id(story_id)
        new_count = self.repository.increment_likes(story_id)
        newly_earned = []
        if story and getattr(story, 'author_id', None) is not None:
            newly_earned = self.gamification_service.evaluate_and_award(story.author_id)
        return new_count, newly_earned
    
    def unlike_story(self, story_id: int) -> Tuple[int, List[Dict[str, Any]]]:
        """Decrement likes for a story. Returns (new_count, newly_earned_badges for story owner)."""
        story = self.repository.find_by_id(story_id)
        new_count = self.repository.decrement_likes(story_id)
        newly_earned = []
        if story and getattr(story, 'author_id', None) is not None:
            newly_earned = self.gamification_service.evaluate_and_award(story.author_id)
        return new_count, newly_earned
    
    def share_story(self, story_id: int) -> Tuple[int, List[Dict[str, Any]]]:
        """Increment shares for a story. Returns (new_count, newly_earned_badges for story owner)."""
        story = self.repository.find_by_id(story_id)
        new_count = self.repository.increment_shares(story_id)
        newly_earned = []
        if story and getattr(story, 'author_id', None) is not None:
            newly_earned = self.gamification_service.evaluate_and_award(story.author_id)
        return new_count, newly_earned
    
    @staticmethod
    def get_categories() -> List[str]:
        """Get list of valid categories."""
        return VALID_CATEGORIES
    
    @staticmethod
    def get_privacy_options() -> List[str]:
        """Get list of valid privacy options."""
        return VALID_PRIVACY_OPTIONS
