from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from runbook_forge.bookstack import is_configured, publish_page
from runbook_forge.generator import generate_runbook
from runbook_forge.storage import RunbookStore

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
DB_PATH = Path(os.getenv("RUNBOOK_FORGE_DB", BASE_DIR / "data" / "runbooks.sqlite3"))
store = RunbookStore(DB_PATH)

app = FastAPI(title="Runbook Forge AI", version="0.1.0")


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "runbooks": store.list_runbooks(),
            "bookstack_configured": is_configured(),
        },
    )


@app.post("/generate", response_class=HTMLResponse)
def generate(
    request: Request,
    title: str = Form(...),
    system: str = Form(""),
    runbook_type: str = Form("Troubleshooting"),
    tags: str = Form(""),
    raw_notes: str = Form(...),
) -> HTMLResponse:
    markdown = generate_runbook(title, system, runbook_type, tags, raw_notes)
    return TEMPLATES.TemplateResponse(
        request,
        "preview.html",
        {
            "request": request,
            "title": title,
            "system": system,
            "runbook_type": runbook_type,
            "tags": tags,
            "raw_notes": raw_notes,
            "markdown": markdown,
            "bookstack_configured": is_configured(),
        },
    )


@app.post("/save")
def save(
    title: str = Form(...),
    system: str = Form(""),
    runbook_type: str = Form("Troubleshooting"),
    tags: str = Form(""),
    raw_notes: str = Form(""),
    markdown: str = Form(...),
) -> RedirectResponse:
    record = store.create_runbook(
        title=title,
        system=system,
        runbook_type=runbook_type,
        tags=tags,
        raw_notes=raw_notes,
        markdown=markdown,
    )
    return RedirectResponse(f"/runbooks/{record.id}", status_code=303)


@app.get("/runbooks/{record_id}", response_class=HTMLResponse)
def detail(request: Request, record_id: int) -> HTMLResponse:
    record = store.get_runbook(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return TEMPLATES.TemplateResponse(
        request,
        "detail.html",
        {
            "request": request,
            "runbook": record,
            "bookstack_configured": is_configured(),
            "message": None,
            "error": None,
        },
    )


@app.post("/runbooks/{record_id}/update")
def update(record_id: int, markdown: str = Form(...)) -> RedirectResponse:
    record = store.update_markdown(record_id, markdown)
    if record is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RedirectResponse(f"/runbooks/{record_id}", status_code=303)


@app.post("/runbooks/{record_id}/publish", response_class=HTMLResponse)
def publish(
    request: Request,
    record_id: int,
    book_id: str = Form(""),
    chapter_id: str = Form(""),
) -> HTMLResponse:
    record = store.get_runbook(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    try:
        result = publish_page(
            title=record.title,
            markdown=record.markdown,
            book_id=book_id or None,
            chapter_id=chapter_id or None,
        )
        page_id = str(result.get("id") or result.get("page_id") or "published")
        record = store.mark_published(record_id, page_id) or record
        message = f"Published to BookStack page id {page_id}."
        error = None
    except RuntimeError as exc:
        message = None
        error = str(exc)
    return TEMPLATES.TemplateResponse(
        request,
        "detail.html",
        {
            "request": request,
            "runbook": record,
            "bookstack_configured": is_configured(),
            "message": message,
            "error": error,
        },
    )
