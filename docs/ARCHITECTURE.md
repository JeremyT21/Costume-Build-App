# Cospal Architecture

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React 19 + TypeScript + Vite | Fast, typed, industry standard |
| 3D viewer | three.js via React Three Fiber + drei | Orbit, zoom, and STL loading in the browser |
| API | FastAPI | Async, typed, auto OpenAPI docs at `/docs` |
| Agents | Pydantic AI | Typed tools, validators, and delegation; provider-agnostic |
| Data | SQLite via SQLModel | Zero-setup local storage; swap the URL for Postgres |
| 3D engine | NumPy parametric meshes + software renderer | Watertight STLs and PNG thumbnails sized to the wearer |
| Patterns | SVG drafting from measurements | 1:1 printable sewing patterns |
| Products | Rainforest API (optional) | Structured Amazon search and reviews |

## Request flow

1. **Survey**: height, weight, build, budget tier, allowed methods, and start mode
   produce estimated measurements (`app/sizing.py`).
2. **Analyze** (`POST /api/costumes/analyze`): concept → component → fabrication agents
   run for each concept and are stored as drafts.
3. **Select** (`POST /api/costumes/select`): the chosen concept (and any kept ones) is
   saved; modeling and shopping agents fan out in parallel per component.
4. **Track**: buy/build decisions, step checklists, and completion update the progress bar.
5. **Rescale**: saving a new survey rebuilds every 3D model at the new size.

## Data model

- `Profile`: one row per user: body, budget, allowed methods, defaults.
- `Costume`: a concept or saved costume, grouped by `draft_group`.
- `Component`: one piece with status (`undecided`, `buying`, `building`,
  `completed`), method, plan, products, sizing, and 3D model spec.

## What must be done in advance

Before production use:

1. **Choose an LLM** with vision and tool calling, and set `COSPAL_MODEL` plus that
   provider's API key in `backend/.env`. Without one, Cospal runs in offline mode.
2. **Amazon data**: create a Rainforest API account (or another provider), set
   `AMAZON_PROVIDER=rainforest` and `RAINFOREST_API_KEY`. Join Amazon Associates for an
   affiliate tag if you plan to earn on referrals. Product data must follow Amazon's terms.
3. **Image-to-3D (future)**: organic shapes (creature heads, sculpted props) need an
   open image-to-3D model such as TripoSR, TRELLIS, or Hunyuan3D on a GPU host.
   Parametric templates already cover wearable armor and props.
4. **Accounts and storage**: add authentication and move SQLite and uploads to
   Postgres and object storage before hosting for multiple users.
5. **Future purchasing and printing**: buying through the app needs the Amazon
   Selling Partner or Creators API; one-click printing needs a printer API such as
   OctoPrint, Bambu Lab, or Prusa Connect. Both are out of scope today; users mark
   items bought or printed themselves.
6. **Legal**: a privacy policy covering body measurements and photos, and IP
   guidance for character likenesses.

## Pydantic AI vs LangGraph

**Decision: Pydantic AI.**

| Need | Pydantic AI | LangGraph |
| --- | --- | --- |
| Structured outputs for UI cards | Native typed `output_type`, validated by Pydantic | Possible via structured output helpers |
| Self-correction | `output_validator` + `ModelRetry` built in | Model as graph edges and conditional loops |
| Tool calling | Decorated, typed functions with dependency injection | Tool nodes in a graph |
| Agent-to-agent | Delegation inside tools with shared usage limits | Subgraphs and supervisor patterns |
| Long-running, resumable state | Basic (message history) | Strong: checkpointers and durable execution |
| Human-in-the-loop pauses | Deferred tools | First-class interrupts |
| Testing | `FunctionModel` / `TestModel` without network | Mock models per node |

Cospal's specialists are short, bounded loops that each return one typed result, and
the orchestration between them is a fixed workflow. That is exactly what Pydantic AI
is designed for, with less boilerplate and stronger typing. The human checkpoint
(picking a concept) is handled by the API itself.

**Revisit LangGraph** if builds become long-running conversations that must pause for
days, resume after crashes, or branch on many human approvals. The agents already
return typed models, so they can become LangGraph nodes without rewriting their logic.
