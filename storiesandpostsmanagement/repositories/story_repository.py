"""
StoryRepository class for SQLite CRUD operations.
Handles all database interactions for story posts.
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from models.story_post import StoryPost


class StoryRepository:
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize the repository with database path."""
        self.db_path = db_path
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create(self, story: StoryPost) -> int:
        """
        Create a new story post in the database.
        Returns the ID of the created story.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            data = story.to_dict()
            del data['id']  # Remove id for insert
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            cursor.execute(
                f"INSERT INTO stories ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def find_by_id(self, story_id: int) -> Optional[StoryPost]:
        """Find a story by its ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
            row = cursor.fetchone()
            
            if row:
                return StoryPost.from_dict(dict(row))
            return None
        finally:
            conn.close()
    
    def find_all(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = 'recent',
        include_deleted: bool = False
    ) -> List[StoryPost]:
        """
        Find all stories with optional filters.
        
        Args:
            search: Search term for caption/description
            category: Filter by category
            sort_by: 'recent', 'likes', or 'comments'
            include_deleted: Whether to include soft-deleted stories
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM stories WHERE 1=1"
            params = []
            
            # Exclude deleted unless requested
            if not include_deleted:
                query += " AND is_deleted = 0"
            
            # Only show published posts (scheduled_at is null or in past)
            query += " AND (scheduled_at IS NULL OR scheduled_at <= ?)"
            params.append(datetime.now().isoformat())
            
            # Search filter
            if search:
                query += " AND (caption LIKE ? OR description LIKE ?)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term])
            
            # Category filter
            if category:
                query += " AND category = ?"
                params.append(category)
            
            # Sorting
            if sort_by == 'likes':
                query += " ORDER BY likes_count DESC"
            elif sort_by == 'comments':
                query += " ORDER BY comments_count DESC"
            else:  # recent
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [StoryPost.from_dict(dict(row)) for row in rows]
        finally:
            conn.close()
    
    def update(self, story: StoryPost) -> bool:
        """
        Update an existing story post.
        Returns True if successful.
        """
        if not story.id:
            return False
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Update the updated_at timestamp
            story.updated_at = datetime.now().isoformat()
            
            data = story.to_dict()
            story_id = data.pop('id')
            
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            
            cursor.execute(
                f"UPDATE stories SET {set_clause} WHERE id = ?",
                list(data.values()) + [story_id]
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def soft_delete(self, story_id: int) -> bool:
        """
        Soft delete a story (mark as deleted).
        Returns True if successful.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE stories SET is_deleted = 1, deleted_at = ? WHERE id = ?",
                (datetime.now().isoformat(), story_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def restore(self, story_id: int) -> bool:
        """
        Restore a soft-deleted story.
        Returns True if successful.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE stories SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
                (story_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def permanent_delete(self, story_id: int) -> bool:
        """
        Permanently delete a story from the database.
        Returns True if successful.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def find_deleted(self) -> List[StoryPost]:
        """Find all soft-deleted stories that are still within the recovery window."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM stories WHERE is_deleted = 1 ORDER BY deleted_at DESC"
            )
            rows = cursor.fetchall()
            
            stories = [StoryPost.from_dict(dict(row)) for row in rows]
            # Filter to only those that can still be restored
            return [s for s in stories if s.can_be_restored()]
        finally:
            conn.close()
    
    def purge_expired(self) -> int:
        """
        Permanently delete stories that have been soft-deleted for more than 7 days.
        Returns the number of stories deleted.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # First, get all deleted stories
            cursor.execute("SELECT * FROM stories WHERE is_deleted = 1")
            rows = cursor.fetchall()
            
            deleted_count = 0
            for row in rows:
                story = StoryPost.from_dict(dict(row))
                if not story.can_be_restored():
                    # Story has expired, permanently delete
                    cursor.execute("DELETE FROM stories WHERE id = ?", (story.id,))
                    deleted_count += 1
            
            conn.commit()
            return deleted_count
        finally:
            conn.close()
    
    def increment_likes(self, story_id: int) -> int:
        """Increment the likes count for a story. Returns the new count."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Use RETURNING clause for atomic update (SQLite 3.35.0+)
            # Fallback to separate SELECT if RETURNING not supported
            try:
                cursor.execute(
                    "UPDATE stories SET likes_count = likes_count + 1 WHERE id = ? RETURNING likes_count",
                    (story_id,)
                )
                row = cursor.fetchone()
                conn.commit()
                return row['likes_count'] if row else 0
            except sqlite3.OperationalError:
                # Fallback for older SQLite versions - use transaction
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    "UPDATE stories SET likes_count = likes_count + 1 WHERE id = ?",
                    (story_id,)
                )
                cursor.execute("SELECT likes_count FROM stories WHERE id = ?", (story_id,))
                row = cursor.fetchone()
                conn.commit()
                return row['likes_count'] if row else 0
        finally:
            conn.close()
    
    def decrement_likes(self, story_id: int) -> int:
        """Decrement the likes count for a story. Returns the new count."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Use RETURNING clause for atomic update (SQLite 3.35.0+)
            # Fallback to separate SELECT if RETURNING not supported
            try:
                cursor.execute(
                    "UPDATE stories SET likes_count = MAX(0, likes_count - 1) WHERE id = ? RETURNING likes_count",
                    (story_id,)
                )
                row = cursor.fetchone()
                conn.commit()
                return row['likes_count'] if row else 0
            except sqlite3.OperationalError:
                # Fallback for older SQLite versions - use transaction
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    "UPDATE stories SET likes_count = MAX(0, likes_count - 1) WHERE id = ?",
                    (story_id,)
                )
                cursor.execute("SELECT likes_count FROM stories WHERE id = ?", (story_id,))
                row = cursor.fetchone()
                conn.commit()
                return row['likes_count'] if row else 0
        finally:
            conn.close()
    
    def increment_shares(self, story_id: int) -> int:
        """Increment the shares count for a story. Returns the new count."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Use RETURNING clause for atomic update (SQLite 3.35.0+)
            # Fallback to separate SELECT if RETURNING not supported
            try:
                cursor.execute(
                    "UPDATE stories SET shares_count = shares_count + 1 WHERE id = ? RETURNING shares_count",
                    (story_id,)
                )
                row = cursor.fetchone()
                conn.commit()
                return row['shares_count'] if row else 0
            except sqlite3.OperationalError:
                # Fallback for older SQLite versions - use transaction
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    "UPDATE stories SET shares_count = shares_count + 1 WHERE id = ?",
                    (story_id,)
                )
                cursor.execute("SELECT shares_count FROM stories WHERE id = ?", (story_id,))
                row = cursor.fetchone()
                conn.commit()
                return row['shares_count'] if row else 0
        finally:
            conn.close()

