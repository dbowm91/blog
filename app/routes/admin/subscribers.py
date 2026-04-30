from __future__ import annotations

from flask import render_template, redirect, url_for, request, flash, Response, abort
from flask_login import login_required

from app.extensions import db
from app.models import Subscriber
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from app.csv_utils import generate_subscribers_csv
from app.config import SUBSCRIBERS_PER_PAGE, EXPORT_BATCH_SIZE
from app.tasks import send_confirmation_task
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/subscribers")
@admin_required
def subscribers() -> Response:
    """
    List all subscribers with pagination and filtering.

    Methods: GET
    GET: Renders subscribers list with pagination.
    Query params:
        page: Page number (default 1)
        status: Filter by status (all, confirmed, unconfirmed, unsubscribed)
    Requires: Admin authentication.
    """
    page = request.args.get("page", 1, type=int)
    filter_status = request.args.get("status", "all")

    base_q = select(Subscriber)
    if filter_status == "confirmed":
        base_q = base_q.filter(Subscriber.confirmed == True)
    elif filter_status == "unconfirmed":
        base_q = base_q.filter(Subscriber.confirmed == False)
    elif filter_status == "unsubscribed":
        base_q = base_q.filter(Subscriber.unsubscribed_at.isnot(None))

    pagination = db.paginate(
        base_q.order_by(Subscriber.created_at.desc()),
        page=page,
        per_page=SUBSCRIBERS_PER_PAGE,
        error_out=False,
    )
    return render_template(
        "admin/subscribers.html",
        subscribers=pagination.items,
        pagination=pagination,
        filter_status=filter_status,
    )


@admin.route("/subscribers/delete/<int:sub_id>", methods=["POST"])
@admin_required
def delete_subscriber(sub_id: int) -> Response:
    """
    Delete a subscriber.

    Methods: POST
    POST: Permanently deletes the subscriber record.
    Requires: Admin authentication.
    Path params: sub_id (int) - ID of the subscriber to delete.
    """
    sub = db.session.get(Subscriber, sub_id)
    if not sub:
        abort(404)
    email = sub.email
    db.session.delete(sub)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.subscribers"))
    logger.info("Subscriber deleted: sub_id=%d email=%s", sub_id, email)
    flash(f"Subscriber {email} deleted.", "success")
    return redirect(url_for("admin.subscribers"))


@admin.route("/subscribers/export")
@admin_required
def export_subscribers() -> Response:
    """
    Export all confirmed subscribers to CSV.

    Methods: GET
    GET: Streams a CSV file with columns: email, subscribed_at, confirmed_at.
    Requires: Admin authentication.
    Response: text/csv with Content-Disposition attachment header.
    """

    def generate():
        offset = 0
        batch_size = EXPORT_BATCH_SIZE
        while True:
            rows = (
                db.session.execute(
                    select(Subscriber)
                    .order_by(Subscriber.created_at.desc())
                    .offset(offset)
                    .limit(batch_size)
                )
                .scalars()
                .all()
            )
            if not rows:
                break
            yield from generate_subscribers_csv(rows)
            offset += batch_size

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers.csv"},
    )


@admin.route("/subscribers/bulk", methods=["POST"])
@admin_required
def subscribers_bulk() -> Response:
    """
    Bulk operations on selected subscribers.

    Methods: POST
    POST: Performs action (delete, export, resend) on selected subscribers.
    Requires: Admin authentication.
    Form params:
        action: One of 'delete', 'export', 'resend'
        sub_ids: List of subscriber IDs to operate on
    Query params: status - preserved for redirect
    """
    action = request.form.get("action")
    sub_ids = request.form.getlist("sub_ids")
    filter_status = request.args.get("status", "all")

    if action in ("delete", "export", "resend"):
        if not sub_ids:
            flash("No subscribers selected.", "error")
            return redirect(url_for("admin.subscribers", status=filter_status))

        valid_ids = []
        for sid in sub_ids:
            try:
                valid_ids.append(int(sid))
            except (ValueError, TypeError):
                flash("Invalid subscriber ID.", "error")
                return redirect(url_for("admin.subscribers", status=filter_status))

        if action == "delete":
            subs = (
                db.session.execute(
                    select(Subscriber).filter(Subscriber.id.in_(valid_ids))
                )
                .scalars()
                .all()
            )
            count = len(subs)
            for sub in subs:
                db.session.delete(sub)
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
                flash("Database error occurred. Please try again.", "error")
                return redirect(url_for("admin.subscribers"))
            flash(f"Deleted {count} subscriber(s).", "success")
        elif action == "export":
            subs = (
                db.session.execute(
                    select(Subscriber)
                    .filter(Subscriber.id.in_(valid_ids))
                    .order_by(Subscriber.created_at.desc())
                )
                .scalars()
                .all()
            )

            return Response(
                generate_subscribers_csv(subs),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=subscribers_selected.csv"
                },
            )
        elif action == "resend":
            subs = (
                db.session.execute(
                    select(Subscriber).filter(Subscriber.id.in_(valid_ids))
                )
                .scalars()
                .all()
            )
            sent_count = 0
            for sub in subs:
                if sub.confirmed and not sub.unsubscribed_at:
                    continue
                send_confirmation_task.delay(sub.id)
                sent_count += 1
            flash(f"Queued {sent_count} confirmation(s).", "success")

    return redirect(url_for("admin.subscribers", status=filter_status))
