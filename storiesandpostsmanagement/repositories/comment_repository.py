"""
CommentRepository class for SQLite CRUD operations.
Handles all database interactions for comments.
"""
import sqlite3
import os
from typing import Optional, List
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from models.comment import Comment


class CommentRepository:
    """
    Repository class for Comment database operations.
    Implements CRUD operations using SQLite.
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize the repository with database path."""
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create(self, comment: Comment) -> int:
        """
        Create a new comment in the database.
        Also increments the comments_count on the story.
        Returns the ID of the created comment.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Insert the comment
            cursor.execute(
                """INSERT INTO comments (story_id, author_name, author_id, content, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (comment.story_id, comment.author_name, comment.author_id, comment.content, comment.created_at)
            )
            comment_id = cursor.lastrowid
            
            # Increment comments_count on the story
            cursor.execute(
                "UPDATE stories SET comments_count = comments_count + 1 WHERE id = ?",
                (comment.story_id,)
            )
            
            conn.commit()
            return comment_id
        finally:
            conn.close()
    
    def find_by_id(self, comment_id: int) -> Optional[Comment]:
        """Find a comment by its ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
            row = cursor.fetchone()
            
            if row:
                return Comment.from_dict(dict(row))
            return None
        finally:
            conn.close()
    
    def find_by_story_id(self, story_id: int) -> List[Comment]:
        """Find all comments for a story, ordered by creation time (newest first)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM comments WHERE story_id = ? ORDER BY created_at DESC",
                (story_id,)
            )
            rows = cursor.fetchall()
            return [Comment.from_dict(dict(row)) for row in rows]
        finally:
            conn.close()
    
    def delete(self, comment_id: int) -> bool:
        """
        Delete a comment from the database.
        Also decrements the comments_count on the story.
        Returns True if successful.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # First, get the story_id for this comment
            cursor.execute("SELECT story_id FROM comments WHERE id = ?", (comment_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            story_id = row['story_id']
            
            # Delete the comment
            cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
            
            if cursor.rowcount > 0:
                # Decrement comments_count on the story
                cursor.execute(
                    "UPDATE stories SET comments_count = MAX(0, comments_count - 1) WHERE id = ?",
                    (story_id,)
                )
                conn.commit()
                return True
            
            return False
        finally:
            conn.close()
    
    def get_comments_count(self, story_id: int) -> int:
        """Get the number of comments for a story."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM comments WHERE story_id = ?",
                (story_id,)
            )
            row = cursor.fetchone()
            return row['count'] if row else 0
        finally:
            conn.close()
