# Badge & Achievement System — Database Schema

## Reasoning

- **Badges**: Collectible items shown on profile; stored once, many users can earn the same badge.
- **Achievements**: Rules (e.g. "Post 5 stories") that when satisfied award one or more badges.
- **Achievement–Badge**: Many-to-many (one achievement can award multiple badges; one badge can be awarded by multiple achievements).
- **UserBadge / UserAchievement**: Junction tables for "user X earned badge Y at time Z" with unique constraints to prevent duplicate awards.
- **author_id on stories/comments**: Optional placeholder for ownership; used to compute `stories_created_total`, `comments_written_total`, `likes_received_total` (sum of likes on user's stories), `shares_received_total` (sum of shares on user's stories). Nullable so existing data is unchanged.
- **user_activity_dates**: Optional table for `days_active_streak`; one row per (user_id, date) to compute consecutive-day streaks. Stubbed if not implemented.

## Rule types (extensible)

| rule_type                  | Meaning                                  |
|----------------------------|------------------------------------------|
| stories_created_total      | Count of stories where author_id = user  |
| comments_written_total     | Count of comments where author_id = user |
| likes_received_total       | Sum of likes_count on user's stories     |
| shares_received_total      | Sum of shares_count on user's stories    |
| days_active_streak         | Consecutive days with activity (stub)    |

## Tables

### badges
| Column      | Type    | Notes                    |
|------------|---------|--------------------------|
| id         | INTEGER | PK AUTOINCREMENT         |
| title      | TEXT    | e.g. "Storyteller"       |
| description| TEXT    | Optional                 |
| icon_url   | TEXT    | Optional path or URL     |
| sort_order | INTEGER | Display order (default 0)|
| created_at | TEXT    | ISO datetime             |

### achievements
| Column      | Type    | Notes                                      |
|------------|---------|--------------------------------------------|
| id         | INTEGER | PK AUTOINCREMENT                           |
| title      | TEXT    | e.g. "Post 5 stories"                       |
| description| TEXT    | Optional                                   |
| rule_type  | TEXT    | stories_created_total, comments_written_total, etc. |
| rule_value | INTEGER | N in ">= N"                                |
| active     | INTEGER | 1 = active, 0 = disabled                   |
| created_at | TEXT    | ISO datetime                               |

### achievement_badges (many-to-many)
| Column        | Type    | Notes    |
|---------------|---------|----------|
| achievement_id| INTEGER | FK → achievements |
| badge_id      | INTEGER | FK → badges       |
| PRIMARY KEY   | (achievement_id, badge_id) |

### user_badges
| Column   | Type    | Notes                    |
|----------|---------|--------------------------|
| id       | INTEGER | PK AUTOINCREMENT        |
| user_id  | INTEGER | User who earned         |
| badge_id | INTEGER | FK → badges              |
| earned_at| TEXT    | ISO datetime             |
| UNIQUE(user_id, badge_id) | Prevent duplicate awards |

### user_achievements
| Column        | Type    | Notes                    |
|---------------|---------|--------------------------|
| id            | INTEGER | PK AUTOINCREMENT         |
| user_id       | INTEGER | User who earned          |
| achievement_id| INTEGER | FK → achievements        |
| earned_at     | TEXT    | ISO datetime             |
| UNIQUE(user_id, achievement_id) | Prevent duplicate awards |

### Optional: user_activity_dates (for days_active_streak)
| Column      | Type    | Notes           |
|-------------|---------|-----------------|
| user_id     | INTEGER |                 |
| activity_date| TEXT   | DATE (YYYY-MM-DD)|
| UNIQUE(user_id, activity_date) | One row per user per day |

### Schema changes to existing tables (optional / migration)

- **stories**: add `author_id INTEGER` (nullable) — owner for likes_received/shares_received.
- **comments**: add `author_id INTEGER` (nullable) — for comments_written_total.

If columns already exist (e.g. from a previous run), migrations skip adding them.
