"""
Gamification blueprint: /badges, /achievements, /profile/<user_id>/badges,
/admin/badges, /admin/achievements.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth_stub import get_current_user_id, is_mod, require_mod
from services.gamification_service import GamificationService
from repositories.badge_repository import BadgeRepository
from repositories.achievement_repository import AchievementRepository
from config import ACHIEVEMENT_RULE_TYPES
from models.badge import Badge
from models.achievement import Achievement

gamification_bp = Blueprint("gamification", __name__, url_prefix="")
gamification_service = GamificationService()
badge_repo = BadgeRepository()
achievement_repo = AchievementRepository()


# --- Public: badge catalog ---
@gamification_bp.route("/badges")
def badge_catalog():
    """Badge catalog page (all badges)."""
    order_by = request.args.get("order", "sort_order")
    badges = gamification_service.get_badge_catalog(order_by=order_by)
    return render_template("gamification/badge_catalog.html", badges=badges, order_by=order_by)


# --- Public: achievements list ---
@gamification_bp.route("/achievements")
def achievements_list():
    """List achievements (rules)."""
    achievements = achievement_repo.find_all_active(load_badges=True)
    return render_template("gamification/achievements_list.html", achievements=achievements)


# --- Public: user profile badges ---
@gamification_bp.route("/profile/<int:user_id>/badges")
def user_profile_badges(user_id):
    """User's earned badges (and achievements). Sort: newest, rarity, alphabetical."""
    sort_by = request.args.get("sort", "newest")
    badges = gamification_service.get_user_badges(user_id, sort_by=sort_by)
    achievements = gamification_service.get_user_achievements(user_id)
    return render_template(
        "gamification/user_profile_badges.html",
        user_id=user_id,
        badges=badges,
        achievements=achievements,
        sort_by=sort_by,
    )


# --- Admin: badges CRUD ---
@gamification_bp.route("/admin/badges")
def admin_badges_list():
    """Mod: list all badges."""
    require_mod()
    badges = badge_repo.find_all(order_by="sort_order")
    return render_template("gamification/admin/badges_list.html", badges=badges)


@gamification_bp.route("/admin/badges/create", methods=["GET", "POST"])
def admin_badge_create():
    """Mod: create badge."""
    require_mod()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        icon_url = request.form.get("icon_url", "").strip()
        sort_order = request.form.get("sort_order", type=int) or 0
        if not title:
            flash("Title is required", "error")
            return render_template("gamification/admin/badge_form.html", badge=None)
        from datetime import datetime
        badge = Badge(
            title=title,
            description=description or None,
            icon_url=icon_url or None,
            sort_order=sort_order,
            created_at=datetime.now().isoformat(),
        )
        badge_repo.create(badge)
        flash(f"Badge '{title}' created", "success")
        return redirect(url_for(".admin_badges_list"))
    return render_template("gamification/admin/badge_form.html", badge=None)


@gamification_bp.route("/admin/badges/<int:badge_id>/edit", methods=["GET", "POST"])
def admin_badge_edit(badge_id):
    """Mod: edit badge."""
    require_mod()
    badge = badge_repo.find_by_id(badge_id)
    if not badge:
        flash("Badge not found", "error")
        return redirect(url_for(".admin_badges_list"))
    if request.method == "POST":
        badge.title = request.form.get("title", "").strip()
        badge.description = request.form.get("description", "").strip()
        badge.icon_url = request.form.get("icon_url", "").strip()
        badge.sort_order = request.form.get("sort_order", type=int) or 0
        if not badge.title:
            flash("Title is required", "error")
            return render_template("gamification/admin/badge_form.html", badge=badge)
        badge_repo.update(badge)
        flash("Badge updated", "success")
        return redirect(url_for(".admin_badges_list"))
    return render_template("gamification/admin/badge_form.html", badge=badge)


@gamification_bp.route("/admin/badges/<int:badge_id>/delete", methods=["POST"])
def admin_badge_delete(badge_id):
    """Mod: delete badge."""
    require_mod()
    badge = badge_repo.find_by_id(badge_id)
    if not badge:
        flash("Badge not found", "error")
    else:
        badge_repo.delete(badge_id)
        flash("Badge deleted", "success")
    return redirect(url_for(".admin_badges_list"))


# --- Admin: achievements CRUD ---
@gamification_bp.route("/admin/achievements")
def admin_achievements_list():
    """Mod: list all achievements."""
    require_mod()
    achievements = achievement_repo.find_all(load_badges=True)
    return render_template("gamification/admin/achievements_list.html", achievements=achievements)


@gamification_bp.route("/admin/achievements/create", methods=["GET", "POST"])
def admin_achievement_create():
    """Mod: create achievement."""
    require_mod()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        rule_type = request.form.get("rule_type", "").strip()
        rule_value = request.form.get("rule_value", type=int)
        active = request.form.get("active") == "1"
        badge_ids = request.form.getlist("badge_ids", type=int)
        if not title or not rule_type or rule_value is None:
            flash("Title, rule type, and rule value are required", "error")
            badges = badge_repo.find_all()
            return render_template(
                "gamification/admin/achievement_form.html",
                achievement=None,
                rule_types=ACHIEVEMENT_RULE_TYPES,
                badges=badges,
            )
        from datetime import datetime
        achievement = Achievement(
            title=title,
            description=description or None,
            rule_type=rule_type,
            rule_value=rule_value,
            active=active,
            created_at=datetime.now().isoformat(),
            badge_ids=badge_ids,
        )
        achievement_repo.create(achievement, badge_ids=badge_ids)
        flash(f"Achievement '{title}' created", "success")
        return redirect(url_for(".admin_achievements_list"))
    badges = badge_repo.find_all()
    return render_template(
        "gamification/admin/achievement_form.html",
        achievement=None,
        rule_types=ACHIEVEMENT_RULE_TYPES,
        badges=badges,
    )


@gamification_bp.route("/admin/achievements/<int:achievement_id>/edit", methods=["GET", "POST"])
def admin_achievement_edit(achievement_id):
    """Mod: edit achievement."""
    require_mod()
    achievement = achievement_repo.find_by_id(achievement_id, load_badges=True)
    if not achievement:
        flash("Achievement not found", "error")
        return redirect(url_for(".admin_achievements_list"))
    if request.method == "POST":
        achievement.title = request.form.get("title", "").strip()
        achievement.description = request.form.get("description", "").strip()
        achievement.rule_type = request.form.get("rule_type", "").strip()
        achievement.rule_value = request.form.get("rule_value", type=int) or 0
        achievement.active = request.form.get("active") == "1"
        badge_ids = request.form.getlist("badge_ids", type=int)
        if not achievement.title or not achievement.rule_type:
            flash("Title and rule type are required", "error")
            badges = badge_repo.find_all()
            return render_template(
                "gamification/admin/achievement_form.html",
                achievement=achievement,
                rule_types=ACHIEVEMENT_RULE_TYPES,
                badges=badges,
            )
        achievement_repo.update(achievement, badge_ids=badge_ids)
        flash("Achievement updated", "success")
        return redirect(url_for(".admin_achievements_list"))
    badges = badge_repo.find_all()
    return render_template(
        "gamification/admin/achievement_form.html",
        achievement=achievement,
        rule_types=ACHIEVEMENT_RULE_TYPES,
        badges=badges,
    )


@gamification_bp.route("/admin/achievements/<int:achievement_id>/delete", methods=["POST"])
def admin_achievement_delete(achievement_id):
    """Mod: delete achievement."""
    require_mod()
    achievement = achievement_repo.find_by_id(achievement_id)
    if not achievement:
        flash("Achievement not found", "error")
    else:
        achievement_repo.delete(achievement_id)
        flash("Achievement deleted", "success")
    return redirect(url_for(".admin_achievements_list"))
