"""Browse routes - index, archive, tags, search, series, pages."""

import logging
from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    abort,
    Response,
    g,
)
from sqlalchemy import func, or_, select, case
from sqlalchemy.orm import joinedload, defer

from app.extensions import db
from app.models import Post, Tag, Series, PostSeries, post_tags
from app.config import (
    POSTS_PER_PAGE,
    RELATED_POSTS_COUNT,
    FTS_RESULT_LIMIT,
)
from app.tag_cache import _get_tag_counts
from app.search import search as _fts_search, get_search_snippets, get_did_you_mean, get_indexed_terms
from app import limiter, cache as flask_cache

logger = logging.getLogger(__name__)

HARD_RELATED_POST_LIMIT = 20


def _get_cached_tags_and_counts():
    """Get tags and tag counts with request-level caching via Flask g."""
    if not hasattr(g, "_cached_tags"):
        g._cached_tags = (
            db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
        )
    if not hasattr(g, "_cached_tag_counts"):
        g._cached_tag_counts = _get_tag_counts()
    return g._cached_tags, g._cached_tag_counts


@flask_cache.cached(timeout=3600, key_prefix="archive_available_years")
def _get_available_years():
    """Get available years for archive with caching."""
    years_query = (
        select(func.extract("year", Post.created_at).label("year"))
        .filter(Post.published)
        .distinct()
        .order_by(func.extract("year", Post.created_at).desc())
    )
    return [int(row.year) for row in db.session.execute(years_query).fetchall()]


def invalidate_archive_cache():
    """Invalidate archive years cache."""
    flask_cache.delete("archive_available_years")


def _get_related_posts(post):
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    limit = min(RELATED_POSTS_COUNT, HARD_RELATED_POST_LIMIT)
    shared_tags_subq = (
        select(post_tags.c.post_id, func.count(post_tags.c.tag_id).label("shared_count"))
        .filter(
            post_tags.c.tag_id.in_(tag_ids),
            post_tags.c.post_id != post.id,
        )
        .group_by(post_tags.c.post_id)
        .subquery()
    )
    related = (
        db.session.execute(
            select(Post)
            .options(joinedload(Post.tags))
            .join(shared_tags_subq, Post.id == shared_tags_subq.c.post_id)
            .filter(Post.published)
            .order_by(shared_tags_subq.c.shared_count.desc(), Post.created_at.desc())
            .limit(limit)
        )
        .unique()
        .scalars()
        .all()
    )
    return related


def register_browse_routes(public):
    """Register browse-related routes on the Blueprint."""

    @public.route("/")
    @limiter.limit("60 per minute")
    def index() -> Response:
        """Paginated list of published posts with tag sidebar."""
        page = request.args.get("page", 1, type=int)
        pagination = db.paginate(
            select(Post)
            .options(joinedload(Post.tags))
            .filter_by(published=True)
            .order_by(Post.created_at.desc()),
            page=page,
            per_page=POSTS_PER_PAGE,
            error_out=False,
        )
        tags, tag_counts = _get_cached_tags_and_counts()
        return render_template(
            "index.html",
            posts=pagination.items,
            pagination=pagination,
            tags=tags,
            tag_counts=tag_counts,
        )

    ARCHIVE_PER_PAGE = 200

    @public.route("/archive")
    @limiter.limit("30 per minute")
    def archive() -> Response:
        """Chronological archive of all published posts grouped by year/month."""
        year_filter = request.args.get("year", type=int)
        cursor = request.args.get("cursor", type=str)
        direction = request.args.get("direction", "next", type=str)

        available_years = _get_available_years()

        if year_filter and year_filter not in available_years:
            year_filter = None

        cursor_dt = None
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
            except ValueError:
                cursor = None

        posts_query = (
            select(Post)
            .options(joinedload(Post.tags), defer(Post.body))
            .filter(Post.published)
        )

        if year_filter:
            year_start = datetime(year_filter, 1, 1)
            year_end = datetime(year_filter + 1, 1, 1)
            if direction == "prev" and cursor_dt:
                posts_query = posts_query.filter(Post.created_at > cursor_dt, Post.created_at < year_end)
            elif direction == "prev":
                posts_query = posts_query.filter(Post.created_at >= year_start, Post.created_at < year_end)
            elif cursor_dt:
                posts_query = posts_query.filter(Post.created_at < cursor_dt, Post.created_at >= year_start)
            else:
                posts_query = posts_query.filter(Post.created_at >= year_start, Post.created_at < year_end)
        elif cursor_dt:
            posts_query = posts_query.filter(
                Post.created_at < cursor_dt if direction == "next" else Post.created_at > cursor_dt
            )

        posts_query = posts_query.order_by(Post.created_at.desc())

        if direction == "next":
            posts_query = posts_query.limit(ARCHIVE_PER_PAGE)
        else:
            posts_query = posts_query.limit(ARCHIVE_PER_PAGE)

        posts = list(db.session.execute(posts_query).scalars().unique().all())

        archive_data: dict[int, dict[int, list[Post]]] = {}
        for p in posts:
            p_year = p.created_at.year
            p_month = p.created_at.month
            if year_filter and p_year != year_filter:
                continue
            if p_year not in archive_data:
                archive_data[p_year] = {}
            if p_month not in archive_data[p_year]:
                archive_data[p_year][p_month] = []
            archive_data[p_year][p_month].append(p)

        tags, tag_counts = _get_cached_tags_and_counts()

        has_next = len(posts) == ARCHIVE_PER_PAGE and (not year_filter or (year_filter and posts and posts[-1].created_at.year >= year_filter))
        has_prev = cursor is not None and direction == "next"
        next_cursor = posts[-1].created_at.isoformat() if posts and has_next else None
        prev_cursor = posts[0].created_at.isoformat() if posts and has_prev else None

        pagination_info = {
            "has_next": has_next,
            "has_prev": has_prev,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "current_year": year_filter,
            "available_years": available_years,
        }

        return render_template(
            "archive.html",
            archive_data=archive_data,
            tags=tags,
            tag_counts=tag_counts,
            pagination=pagination_info,
        )

    @public.route("/page/<slug>")
    @limiter.limit("60 per minute")
    def page(slug) -> Response:
        """Static content page."""
        from app.models import Page

        page_obj = db.session.execute(
            select(Page).filter_by(slug=slug, published=True)
        ).scalar_one_or_none()
        if not page_obj:
            abort(404)
        return render_template("page.html", page=page_obj)

    @public.route("/tag/<slug>")
    @limiter.limit("60 per minute")
    def tag(slug) -> Response:
        """Posts filtered by tag with pagination."""
        tag_obj = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
        if not tag_obj:
            abort(404)
        page_num = request.args.get("page", 1, type=int)
        pagination = db.paginate(
            select(Post)
            .options(joinedload(Post.tags))
            .filter(Post.published, Post.tags.any(Tag.id == tag_obj.id))
            .order_by(Post.created_at.desc()),
            page=page_num,
            per_page=POSTS_PER_PAGE,
            error_out=False,
        )
        total_posts = pagination.total
        tags, tag_counts = _get_cached_tags_and_counts()
        return render_template(
            "tag.html",
            tag=tag_obj,
            posts=pagination.items,
            pagination=pagination,
            tags=tags,
            tag_counts=tag_counts,
            total_posts=total_posts,
        )

    @public.route("/search")
    @limiter.limit("20 per minute")
    def search() -> Response:
        """Full-text search for published posts."""
        query = request.args.get("q", "", type=str)[:200].strip()
        page_num = request.args.get("page", 1, type=int)

        if not query:
            return redirect("/")

        tags, tag_counts = _get_cached_tags_and_counts()

        post_results = _fts_search(query)
        if post_results:
            if not all(isinstance(r, tuple) and len(r) == 2 for r in post_results):
                logging.warning(f"FTS returned invalid results: {post_results}")
                post_results = []
            post_ids = [pid for pid, _ in post_results]
            pagination = db.paginate(
                select(Post)
                .options(joinedload(Post.tags))
                .filter(Post.published, Post.id.in_(post_ids))
                .order_by(case({pid: rank for pid, rank in post_results}, value=Post.id)),
                page=page_num,
                per_page=POSTS_PER_PAGE,
                error_out=False,
            )
        else:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_term = f"%{escaped}%"
            pagination = db.paginate(
                select(Post)
                .options(joinedload(Post.tags))
                .filter(
                    Post.published,
                    or_(
                        Post.title.ilike(search_term, escape="\\"),
                        Post.body.ilike(search_term, escape="\\"),
                        Post.summary.ilike(search_term, escape="\\"),
                    ),
                )
                .order_by(Post.created_at.desc())
                .limit(FTS_RESULT_LIMIT),
                page=page_num,
                per_page=POSTS_PER_PAGE,
                error_out=False,
            )

        snippets = get_search_snippets(list(pagination.items), query)
        did_you_mean = None
        if not pagination.items:
            indexed_terms = get_indexed_terms()
            did_you_mean = get_did_you_mean(query, indexed_terms)
        return render_template(
            "search.html",
            query=query,
            posts=pagination.items,
            pagination=pagination,
            tags=tags,
            tag_counts=tag_counts,
            search_snippets=snippets,
            did_you_mean=did_you_mean,
        )

    @public.route("/series/<slug>")
    @limiter.limit("60 per minute")
    def series_view(slug) -> Response:
        """View a series and all its posts in order."""
        series = db.session.execute(
            select(Series).filter_by(slug=slug)
        ).scalar_one_or_none()
        if not series:
            abort(404)

        series_posts = (
            db.session.execute(
                select(PostSeries)
                .filter_by(series_id=series.id)
                .order_by(PostSeries.order_index)
            )
            .scalars()
            .all()
        )

        posts = [sp.post for sp in series_posts if sp.post and sp.post.published]

        return render_template(
            "series.html",
            series=series,
            posts=posts,
        )
