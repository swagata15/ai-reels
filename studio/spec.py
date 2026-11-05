"""Reel spec loading and validation (pure Python, no bpy needed)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Instagram Reels: 9:16 vertical, 1080x1920.
REEL_WIDTH = 1080
REEL_HEIGHT = 1920

# Keep important text/subjects out of these bands; Instagram's UI covers them.
SAFE_TOP_PX = 250
SAFE_BOTTOM_PX = 420

DEFAULT_PALETTE = ["#0B0B1A", "#7B5CFF", "#00E5FF", "#FF3D9A"]


@dataclass
class ReelSpec:
    name: str
    template: str
    duration_s: float = 8.0
    fps: int = 30
    seed: int = 7
    palette: list[str] = field(default_factory=lambda: list(DEFAULT_PALETTE))
    text: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    # "draft" = fast preview, "final" = full quality
    quality: str = "final"

    @property
    def frames(self) -> int:
        return max(1, round(self.duration_s * self.fps))

    @classmethod
    def from_dict(cls, data: dict) -> "ReelSpec":
        missing = [k for k in ("name", "template") if k not in data]
        if missing:
            raise ValueError(f"Reel spec missing required keys: {missing}")
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown keys in reel spec: {sorted(unknown)}")
        spec = cls(**data)
        if spec.quality not in ("draft", "final"):
            raise ValueError("quality must be 'draft' or 'final'")
        if not 1 <= spec.duration_s <= 180:
            raise ValueError("duration_s must be between 1 and 180 seconds")
        if len(spec.palette) < 2:
            raise ValueError("palette needs at least 2 colours (background + accent)")
        return spec

    @classmethod
    def load(cls, path: str | Path) -> "ReelSpec":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


def hex_to_rgba(value: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """'#RRGGBB' -> linear RGBA floats (Blender works in linear colour)."""
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB colour, got {value!r}")
    srgb = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (to_linear(c) for c in srgb)
    return (r, g, b, alpha)
