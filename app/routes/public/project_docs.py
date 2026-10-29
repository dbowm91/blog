from __future__ import annotations

from flask import abort, render_template
from flask.typing import ResponseReturnValue

from app.services import project_docs
from app.services.projects import get_published_project


def register_project_docs_routes(public) -> None:
    @public.route("/projects/<slug>/docs")
    def project_docs_home(slug: str) -> ResponseReturnValue:
        project = get_published_project(slug)
        if project is None or not project.docs_enabled:
            abort(404)
        document = project_docs.home_document(project)
        if document is None:
            abort(404)
        return _render(project, document)

    @public.route("/projects/<slug>/docs/<path:doc_path>")
    def project_doc(slug: str, doc_path: str) -> ResponseReturnValue:
        project = get_published_project(slug)
        if project is None or not project.docs_enabled:
            abort(404)
        try:
            normalized = project_docs.normalize_document_path(doc_path)
        except project_docs.DocumentPathError:
            abort(404)
        document = project_docs.get_document(project, normalized)
        if document is None:
            abort(404)
        return _render(project, document)


def _render(project, document):
    documents = project_docs.list_documents(project.id)
    document_index = next(
        (index for index, item in enumerate(documents) if item.id == document.id),
        None,
    )
    return render_template(
        "projects/docs.html",
        project=project,
        document=document,
        documents=documents,
        document_index=document_index,
        rendered_body=project_docs.render_document(project, document),
    )
