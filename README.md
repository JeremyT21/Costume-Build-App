# Cospal

Cospal helps you plan, make, and buy cosplay costumes. Upload or snap a picture of a
character and a team of AI agents breaks it into components, decides what to buy and
what to build within your budget, designs printable 3D parts sized to your body, drafts
sewing and knitting patterns, finds products, and tracks your progress to a finished
costume.

## Features

- **Sizing survey**: height, weight, and build estimate your measurements; enter exact
  values to override them.
- **Budget tiers** with fixed ranges, from Shoestring (under $75) to Showpiece ($1200+).
- **Method preferences**: allow everything, 3D print only, Amazon only, or any mix.
- **Character analysis**: separates skin paint and makeup from pieces that must be made.
- **Concept picker**: upload different versions and choose from the top 3; any can be
  saved to your collection.
- **Buy or build per component**, or set buy-all or build-all for a whole costume.
- **Switch methods** per component (for example knit ↔ 3D print); files regenerate.
- **Body-scaled 3D models**: watertight STL files, thumbnails, a rotatable viewer, and
  file info (size, triangles, dimensions, bed fit, filament, print time).
- **Body map**: every piece pinned on a human silhouette, showing the product photo for
  purchases and the 3D render for builds. Tap any piece for details.
- **Sewing patterns** (1:1 SVG) and **knitting patterns** from your measurements.
- **Amazon recommendations** with review-based size advice.
- **Progress tracking**: step checklists auto-complete components; the progress bar
  splits built, bought, and in-progress pieces.
- **Filters and sorting**: buying, building, completed, suggested to buy or build,
  ready to improve.
- **Improvement advice**: upload photos of your build for a critique.

## Quick start

Requirements: Python 3.11+ and Node.js 20+.

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # Set COSPAL_MODEL and your provider key to enable agents
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

Without a model configured, Cospal runs in **offline mode**: components are inferred
from your description and plans come from built-in rules. Everything else works,
including 3D models, patterns, and tracking.

## Tests

```bash
cd backend && pytest -q
cd frontend && npx tsc -b && npx oxlint src
```

## Project layout

```
backend/
  app/agents/      Specialist agents, orchestrator, offline rules
  app/services/    3D mesh engine, renderer, patterns, knitting, Amazon client
  app/main.py      HTTP API
  tests/           Agent loop, geometry, tailoring, and API tests
frontend/
  src/pages/       Onboarding, collection, new costume, costume workspace
  src/components/  Body map, 3D viewer, component drawer, shared UI
docs/
  AGENTS.md        Agent design, patterns, and references
  ARCHITECTURE.md  Stack, prerequisites, Pydantic AI vs LangGraph
  CONVENTIONS.md   Coding conventions
```

## Roadmap

- Buy on Amazon and send prints to a printer from inside the app.
- Image-to-3D for organic shapes through a self-hosted open model.
- Accounts and cloud sync.
