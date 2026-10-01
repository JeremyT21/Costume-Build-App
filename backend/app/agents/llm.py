"""Shared agent construction, execution limits, and vision tools."""

from __future__ import annotations

import io
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from PIL import Image
from pydantic_ai import Agent, BinaryContent, ToolReturn
from pydantic_ai.usage import UsageLimits

from app.config import settings

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT")
DepsT = TypeVar("DepsT")

# Caps each agent loop so a confused model cannot spin forever.
DEFAULT_LIMITS = UsageLimits(request_limit=16, tool_calls_limit=24)

_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif"}


def build_agent(
    name: str,
    output_type: type[OutputT],
    instructions: str,
    deps_type: type[DepsT],
) -> Agent[DepsT, OutputT]:
    return Agent(
        settings.model,
        name=name,
        output_type=output_type,
        instructions=instructions,
        deps_type=deps_type,
        retries=3,
        defer_model_check=True,
    )


def image_parts(paths: Sequence[Path]) -> list[BinaryContent]:
    return [BinaryContent(data=p.read_bytes(),
                          media_type=_MEDIA_TYPES.get(p.suffix.lower(), "image/jpeg"))
            for p in paths]


async def run_agent(
    agent: Agent[DepsT, OutputT],
    prompt: str,
    deps: DepsT,
    images: Sequence[Path] = (),
    limits: UsageLimits = DEFAULT_LIMITS,
) -> OutputT | None:
    """Run an agent loop; returns None when AI is off or the run fails."""
    if not settings.llm_enabled:
        return None
    try:
        result = await agent.run([prompt, *image_parts(images)], deps=deps, usage_limits=limits)
    except Exception:  # noqa: BLE001  Any provider failure falls back to heuristics.
        logger.exception("Agent %s failed", agent.name)
        return None
    return result.output


def zoom(images: Sequence[Path], index: int, left: float, top: float, right: float,
         bottom: float) -> ToolReturn:
    """Crop a region given as 0-1 fractions and return it enlarged to the model."""
    if not 0 <= index < len(images):
        return ToolReturn(return_value=f"No image at index {index}; there are {len(images)}.")
    with Image.open(images[index]) as img:
        w, h = img.size
        box = (int(max(0, left) * w), int(max(0, top) * h),
               int(min(1, right) * w), int(min(1, bottom) * h))
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            return ToolReturn(return_value="Region too small; widen the crop.")
        crop = img.convert("RGB").crop(box)
        crop.thumbnail((1024, 1024))
        buffer = io.BytesIO()
        crop.save(buffer, format="JPEG", quality=90)
    return ToolReturn(
        return_value=f"Zoomed image {index} region {box}.",
        content=[BinaryContent(data=buffer.getvalue(), media_type="image/jpeg")],
    )
