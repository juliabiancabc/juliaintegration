# Badge & Achievement System — Test Plan

## Manual tests

1. **Database**
   - Run `python init_db.py` (or start app so init_db runs). Confirm no errors and that tables `badges`, `achievements`, `achievement_badges`, `user_badges`, `user_achievements`, `user_activity_dates` exist (e.g. via SQLite browser or `sqlite3 data/stories.db ".tables"`).

2. **Public routes**
   - **Badge catalog**: GET `/badges`. Expect empty list or list of badges. Try query `?order=title` and `?order=newest`.
   - **Achievements**: GET `/achievements`. Expect list of active achievements or empty.
   - **User profile badges**: GET `/profile/1/badges`. Expect badges/achievements for user 1 (or empty). Try `?sort=rarity` and `?sort=alphabetical`.

3. **Admin routes (mod required)**
   - Without mod: GET `/admin/badges` and `/admin/achievements` should return 403.
   - With mod: open `/admin/badges?mod=1` (or set `session['is_mod'] = True`). Create a badge (title, description, icon_url, sort_order). Edit and delete it.
   - With mod: open `/admin/achievements?mod=1`. Create an achievement (title, rule_type e.g. `stories_created_total`, rule_value e.g. 1, select one or more badges). Edit and delete.

4. **Automation hooks**
   - **Story created**: Create a story with `?user_id=1` (or pass user_id in form/session so `get_current_user_id()` returns 1). Ensure story has `author_id=1`. Create an achievement "stories_created_total >= 1" awarding a badge. Create the story again as user 1; expect newly earned badge (flash or JSON).
   - **Like / share**: Create a story with author_id=1. Create achievement "likes_received_total >= 1" (or shares) awarding a badge. Like or share that story (AJAX). Expect response to include `newly_earned_badges`.
   - **Comment**: Add comment with `author_id=1` (e.g. in JSON body). Create achievement "comments_written_total >= 1". Add comment; expect `newly_earned_badges` in JSON response.

5. **Duplicate awards**
   - Earn an achievement once (e.g. stories_created_total >= 1). Trigger the same condition again (e.g. create another story). Confirm the same badge is not awarded again (no duplicate row in `user_badges` / `user_achievements`).

6. **Sorting**
   - User profile badges: confirm sort options (newest, rarity, alphabetical) change order.

---

## Automated test ideas

1. **Unit: GamificationService.evaluate_and_award**
   - Mock `UserProgressRepository.get_user_stats` to return e.g. `stories_created_total: 5`. Mock `AchievementRepository.find_all_active` to return one achievement with rule `stories_created_total >= 5` and one badge_id. Mock `UserProgressRepository.has_achievement` to False, and `award_achievement` / `award_badge` to True. Call `evaluate_and_award(user_id=1)`. Assert result list contains one badge dict and that `award_achievement` and `award_badge` were called.

2. **Integration: award on story create**
   - Use a test DB and init_db. Insert one badge and one achievement (stories_created_total >= 1) linking that badge. Call `StoryService().create_story(..., current_user_id=1)` (minimal valid caption/description/category/privacy). Assert returned `newly_earned_badges` has one entry and that `user_badges` and `user_achievements` each have one row for user 1.

3. **Integration: no duplicate award**
   - Same setup as above. Call `create_story` twice for the same user. Assert `newly_earned_badges` has one badge the first time and zero the second time; assert `user_badges` has exactly one row for that user and badge.
