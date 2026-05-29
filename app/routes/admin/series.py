from __future__ import annotations

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort,
)
from flask.typing import ResponseReturnValue

from app.extensions import db
from app.models import Series, Post, PostSeries
from app.routes.admin import admin, admin_required
from app.utils import generate_slug
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import joinedload


@admin.route("/series")
@admin_required
def series_list() -> ResponseReturnValue:
    """List all series with post counts."""
    series_with_counts = db.session.execute(
        select(Series, func.count(PostSeries.id).label("post_count"))
        .outerjoin(PostSeries)
        .group_by(Series.id)
        .order_by(Series.created_at.desc())
    ).all()

    return render_template(
        "admin/series.html",
        series_with_counts=series_with_counts,
    )


@admin.route("/series/new", methods=["GET", "POST"])
@admin_required
def series_new() -> ResponseReturnValue:
    """Create a new series."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Series name is required.", "error")
            return render_template("admin/series_editor.html", series=None)

        # Generate slug from name
        slug = request.form.get("slug", "").strip()
        if not slug:
            slug = generate_slug(name)
        else:
            slug = generate_slug(slug)

        # Check for slug uniqueness
        existing = db.session.execute(select(Series).filter_by(slug=slug)).scalar_one_or_none()
        if existing:
            flash(f"A series with slug '{slug}' already exists.", "error")
            return render_template("admin/series_editor.html", series=None)

        series = Series(
            name=name,
            slug=slug,
            description=description,
        )

        try:
            db.session.add(series)
            db.session.commit()
            flash(f"Series '{name}' created successfully.", "success")
            return redirect(url_for("admin.series_list"))
        except (IntegrityError, OperationalError) as e:
            db.session.rollback()
            flash(f"Error creating series: {str(e)}", "error")
            return render_template("admin/series_editor.html", series=None)

    return render_template("admin/series_editor.html", series=None)


@admin.route("/series/<int:series_id>/edit", methods=["GET", "POST"])
@admin_required
def series_edit(series_id: int) -> ResponseReturnValue:
    """Edit an existing series and manage its posts."""
    series = db.session.get(Series, series_id)
    if not series:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        slug = request.form.get("slug", "").strip()

        if not name:
            flash("Series name is required.", "error")
            return render_template("admin/series_editor.html", series=series)

        if not slug:
            slug = generate_slug(name)
        else:
            slug = generate_slug(slug)

        # Check for slug uniqueness (excluding current series)
        existing = db.session.execute(
            select(Series).filter(Series.slug == slug, Series.id != series_id)
        ).scalar_one_or_none()
        if existing:
            flash(f"A series with slug '{slug}' already exists.", "error")
            return render_template("admin/series_editor.html", series=series)

        series.name = name
        series.slug = slug
        series.description = description

        try:
            db.session.commit()
            flash(f"Series '{name}' updated successfully.", "success")
            return redirect(url_for("admin.series_list"))
        except (IntegrityError, OperationalError) as e:
            db.session.rollback()
            flash(f"Error updating series: {str(e)}", "error")

    return render_template("admin/series_editor.html", series=series)


@admin.route("/series/<int:series_id>/delete", methods=["POST"])
@admin_required
def series_delete(series_id: int) -> ResponseReturnValue:
    """Delete a series and its post associations."""
    series = db.session.get(Series, series_id)
    if not series:
        abort(404)

    name = series.name

    try:
        # Delete post associations first
        db.session.execute(PostSeries.__table__.delete().where(PostSeries.series_id == series_id))
        db.session.delete(series)
        db.session.commit()
        flash(f"Series '{name}' deleted successfully.", "success")
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        flash(f"Error deleting series: {str(e)}", "error")

    return redirect(url_for("admin.series_list"))


@admin.route("/series/<int:series_id>/posts", methods=["GET", "POST"])
@admin_required
def series_posts(series_id: int) -> ResponseReturnValue:
    """Manage posts in a series."""
    series = db.session.get(Series, series_id)
    if not series:
        abort(404)

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "add":
            post_id = request.form.get("post_id", type=int)
            if post_id:
                # Check if already in series
                existing = db.session.execute(
                    select(PostSeries).filter_by(series_id=series_id, post_id=post_id)
                ).scalar_one_or_none()

                if existing:
                    flash("Post is already in this series.", "warning")
                else:
                    # Get next order_index
                    max_order = (
                        db.session.execute(
                            select(func.max(PostSeries.order_index)).filter_by(series_id=series_id)
                        ).scalar()
                        or 0
                    )

                    post_series = PostSeries(
                        series_id=series_id,
                        post_id=post_id,
                        order_index=max_order + 1,
                    )
                    db.session.add(post_series)
                    try:
                        db.session.commit()
                        flash("Post added to series.", "success")
                    except (IntegrityError, OperationalError) as e:
                        db.session.rollback()
                        flash(f"Error adding post to series: {str(e)}", "error")

        elif action == "remove":
            post_series_id = request.form.get("post_series_id", type=int)
            if post_series_id:
                ps = db.session.get(PostSeries, post_series_id)
                if ps and ps.series_id == series_id:
                    db.session.delete(ps)
                    db.session.commit()
                    flash("Post removed from series.", "success")

        elif action == "reorder":
            # Update order_index for multiple posts
            post_order = request.form.getlist("post_order[]")
            for index, ps_id in enumerate(post_order, 1):
                ps = db.session.get(PostSeries, int(ps_id))
                if ps and ps.series_id == series_id:
                    ps.order_index = index
            try:
                db.session.commit()
                flash("Series order updated.", "success")
            except (IntegrityError, OperationalError) as e:
                db.session.rollback()
                flash(f"Error updating order: {str(e)}", "error")

        return redirect(url_for("admin.series_posts", series_id=series_id))

    # GET request - show posts in series and available posts
    series_posts = (
        db.session.execute(
            select(PostSeries)
            .options(joinedload(PostSeries.post))
            .filter_by(series_id=series_id)
            .order_by(PostSeries.order_index)
        )
        .scalars()
        .unique()
        .all()
    )

    # Get posts not in this series (published only)
    subq = select(PostSeries.post_id).filter_by(series_id=series_id).scalar_subquery()
    available_posts = (
        db.session.execute(
            select(Post).filter(Post.published, ~Post.id.in_(subq)).order_by(Post.created_at.desc())
        )
        .scalars()
        .all()
    )

    return render_template(
        "admin/series_posts.html",
        series=series,
        series_posts=series_posts,
        available_posts=available_posts,
    )


@admin.route("/series/<int:series_id>/reorder", methods=["POST"])
@admin_required
def series_reorder(series_id: int) -> ResponseReturnValue:
    """Update the order of posts in a series via AJAX."""
    from flask import jsonify

    series = db.session.get(Series, series_id)
    if not series:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json()
    if not data or "order" not in data:
        return jsonify({"error": "Invalid request"}), 400

    try:
        for item in data["order"]:
            ps_id = item.get("id")
            order = item.get("order")
            ps = db.session.get(PostSeries, ps_id)
            if ps and ps.series_id == series_id:
                ps.order_index = order

        db.session.commit()
        return jsonify({"success": True})
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
