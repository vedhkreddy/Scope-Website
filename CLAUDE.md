# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (port 5005)
python app.py

# Run production server (as deployed)
gunicorn app:app
```

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SCOPE_SECRET_KEY` | `dev-secret` | Flask session secret |
| `SCOPE_ADMIN_PASSWORD` | `changeme` | Admin portal password |
| `PORT` | `5005` | Dev server port |

## Architecture

This is a single-file Flask app (`app.py`) with no database — all content is stored in `content.json` and loaded/saved on every request via `load_content()` / `save_content()`. Uploaded images go to `static/uploads/` and PDFs to `static/pdfs/` (both gitignored).

**Content sections in `content.json`:**
- `site` — title and mascot image URL
- `current_edition` / `current_edition_title` / `current_edition_pdf_url` — homepage featured edition
- `publications` — list of journal issues (sorted by date descending)
- `news` — "Science in the News" articles with preview + full_text fields
- `about` — team members with an `order` integer for manual ordering
- `submission_guide` — Markdown string rendered with `markdown2`

**Admin portal** is at `/admin`, gated by a simple password stored in the session. All admin routes check `'admin' not in session` and redirect to login. There is no CSRF protection.

**Templates** all extend `base.html` via `{% block content %}` and expect a `content` variable (the full `content.json` dict) to be passed by the route, used to render nav/footer site metadata.

**File upload naming:** uploaded files are prefixed with their content type and a UUID hex (e.g. `news_<uuid>_<original_name>`). Old files are deleted when replaced for the edition PDF and mascot, but not for publications or news images.
