# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PaperShelf: a tiny static site that shows exam questions (one image per question) to a kid on a tablet/PC, who answers on paper. `DESIGN.md` (Traditional Chinese) is the authoritative spec — **if the spec needs to change, edit DESIGN.md first, then the code.** Its §2 principles and §3 "explicitly not doing" list are binding: no question generation, no image processing, no answer storage/display, no custom zoom, no backend for the published site. New features need an explicit reason.

## Running

No build, no dependencies, no tests, no linter. Python 3 stdlib only.

```bash
./start-packager.sh          # Ubuntu (opens browser); Windows: start-packager.bat
python3 packager/server.py   # server only → http://localhost:8420 (bound to 127.0.0.1)
```

## Architecture

Two separate halves:

1. **Packager (local only)** — `packager/server.py` is a stdlib `http.server` that only does file I/O and git proxying:
   - `GET /api/images` lists `source-images/` (recursive, jpg/png/webp); `GET /api/image/<path>` serves one.
   - `POST /api/exam` writes `docs/exams/<id>.html`; `POST /api/manifest` (`action: add|delete`) edits `manifest.json` (delete also removes the exam HTML); `POST /api/index` regenerates `docs/index.html`; `POST /api/publish` runs `git add -A && git commit && git push` in the repo root.
   - Frontend in `packager/static/` (`app.js`): pick images → queue/reorder → per-question scale % → preview → save → publish. Images are fetched and converted to base64 data URLs in the browser.
2. **Published site** — `docs/` is the GitHub Pages root (https://emissionspectrum-creator.github.io/PaperShelf/). Everything in it is generated; never hand-edit `docs/index.html` or `docs/exams/*.html`.

Key invariants spanning files:

- **`packager/static/exam-template.js` `buildExamHtml()` is the single source of exam HTML.** The preview iframe (`srcdoc`) and the saved file both use it — preview must never use separate display logic (DESIGN §6). Exam HTML must stay single-file with base64-embedded images, relative widths (no fixed px widths), no `user-scalable=no`, one question per viewport via CSS `scroll-snap`, off-white `#f5f4f0` background (not pure white, not dark).
- `docs/index.html` is rendered by `render_index_html()` in `server.py`, sorted by `addedAt` descending, filterable by grade/subject.
- `manifest.json` is the only persistent state (versioned in git). Entry id format is `年級-科目-序號` with 3-digit zero-padded seq (e.g. `國小一年級-數學-001`), which is also the exam filename. Grades are 國小一～六年級; subjects are 國文、數學 (hard-coded in `app.js` `GRADES`/`SUBJECTS`).
- **Privacy:** the repo and site are public. Filenames, page titles, and index entries must never contain the child's name or school name.

## Question image guidance

Upstream images should be ~2× display resolution: exam frame is ~900px wide, max 92vh tall, so target ~1800px wide, aspect 1:1 to 4:5 (w:h). DESIGN.md §5 contains the SVG and HTML prompt templates for generating question images with Claude.
