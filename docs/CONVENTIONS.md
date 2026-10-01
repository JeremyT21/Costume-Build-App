# Cospal Coding Conventions

Every contributor follows this file so the codebase reads as one voice.
The rules build on these references:

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [Google HTML/CSS Style Guide](https://google.github.io/styleguide/htmlcssguide.html)
- [PEP 8](https://peps.python.org/pep-0008/) and [PEP 484](https://peps.python.org/pep-0484/) type hints

## 1. Comments

- A comment is **at most 2 lines** long.
- Comments are simple and concise. State what the code does or why it exists.
- Comments never compare one approach with another ("faster than X", "unlike Y").
- Prefer clear names over comments. Delete comments that restate the code.
- Python docstrings follow the same 2-line limit: one summary line, plus one optional detail line.
- `TODO(username): short task` is the only allowed TODO format.

## 2. Python (backend)

| Topic | Rule |
| --- | --- |
| Version | Python 3.11+ |
| Formatting | 4-space indent, max line length 100, double quotes |
| Naming | `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants, `_private` helpers |
| Imports | `from __future__ import annotations` first; then stdlib, third-party, local; one group each, sorted |
| Types | Every public function has full type hints. Use `X \| None`, `list[str]`, never `Optional`/`List` |
| Data | API and agent payloads are Pydantic models. Database tables are SQLModel classes in `models.py` |
| Errors | Raise specific exceptions. Never use bare `except:`. API errors use `HTTPException` |
| Async | Route handlers and agent calls are `async`. Blocking I/O stays out of async paths |
| Config | Settings come from environment variables via `app/config.py` only |
| Tests | `pytest`, files named `test_*.py`, one behavior per test |

### Agents

- One agent per file in `app/agents/`, each exposing a single `async def` entry point.
- Every agent has a deterministic offline fallback so the app runs without an API key.
- Agents return typed Pydantic models from `app/schemas.py`, never raw strings or dicts.

## 3. TypeScript / React (frontend)

| Topic | Rule |
| --- | --- |
| Formatting | 2-space indent, single quotes, semicolons, trailing commas |
| Naming | `camelCase` variables/functions, `PascalCase` components/types, `UPPER_SNAKE` constants |
| Files | Components are `PascalCase.tsx`; everything else is `camelCase.ts` |
| Exports | Named exports only. No `default` exports |
| Types | `strict` mode on. No `any`. Prefer `interface` for object shapes, `type` for unions |
| Components | Function components with hooks. One component per file. Props typed with an interface |
| Data | All HTTP calls live in `src/api.ts`. Shared types live in `src/types.ts` |
| Styling | CSS custom properties in `src/styles.css`. Class names use `kebab-case` |
| Equality | Always `===` / `!==` |

### Visual design

- Dark only: graphite base (`--bg`, `--surface*`) with violet, rose, and blue ambient light.
- Accent colors come from `--accent-h`, `--accent-2-h`, `--accent-3-h`. Never hard-code an accent hex.
- Costume pages call `useCostumeTheme` so the app takes on that costume's hue; other pages use the default.
- Status colors: building uses the accent, completed is green, buying and bought are silver.
- Type: Bricolage Grotesque for headings and large numbers, Instrument Sans for interface text.
- Labels use sentence case. No all-caps eyebrows and no middle-dot meta strings; use `.facts` spans.

### Motion

- Every transition and animation uses the tokens `--dur-fast`, `--dur`, `--dur-slow`, `--dur-theme` and `--ease`.
- Entrance animations use `backwards` fill so finished animations leave no transform behind.
- Motion answers user actions; the only automatic sequences are the page entrance and the body map reveal.
- The Animations switch sets `data-motion` on `<html>`; system reduced-motion is the default.
- Fixed overlays (drawers, dialogs) render through a portal to `document.body`.

## 4. Shared domain vocabulary

Use these exact terms everywhere (code, UI, docs):

- **Costume**: one character build in the collection.
- **Component**: one piece of a costume (helmet, cape, face paint).
- **Category**: `armor`, `clothing`, `prop`, `accessory`, `footwear`, `wig`, `body_paint`, `makeup`.
- **Method**: `3d_print`, `sew`, `knit`, `foam_craft`, `paint`, `thrift_modify`, `buy`.
- **Status**: `undecided`, `buying`, `building`, `completed`.
- **Budget tier**: `shoestring`, `budget`, `standard`, `premium`, `showpiece`.

## 5. Git

- Branch names: `feature/<short-name>`, `fix/<short-name>`.
- Commit subject in imperative mood, max 72 characters ("Add sizing agent").
- One logical change per commit.
