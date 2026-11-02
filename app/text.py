"""Text rendering helpers for Pillow: per-character font fallback, fitting, ellipsis.

Pillow draws a string with a single font, so a name like "Spoon Fed ⚽ 東京" needs to
be split into runs, each drawn with the first font in a stack that has its glyphs.
Characters no bundled font covers are dropped rather than drawn as "tofu" boxes;
callers can use legible() to fall back to other text when nothing readable is left.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
ELLIPSIS = "…"

# Characters that never start a new run: they stick to the character before them.
_JOINERS = {"‍", "︎", "️", "⃣"}
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f​  ‪-‮⁦-⁩]")


def _is_attached(ch: str) -> bool:
    return (
        ch in _JOINERS
        or unicodedata.category(ch) in ("Mn", "Me", "Mc")
        or 0x1F3FB <= ord(ch) <= 0x1F3FF  # skin-tone modifiers
        or 0xE0020 <= ord(ch) <= 0xE007F  # tag characters (flag sequences)
    )


def clean(text: str) -> str:
    """Normalise user-supplied names: NFC, no control/bidi-override chars, single spaces."""
    text = unicodedata.normalize("NFC", text or "")
    text = _CONTROL.sub("", text)
    return " ".join(text.split())


def clusters(text: str) -> list[str]:
    """Split into user-perceived characters (close enough for truncation purposes)."""
    def regional(c: str) -> bool:
        return 0x1F1E6 <= ord(c) <= 0x1F1FF

    out: list[str] = []
    for ch in text:
        flag_pair = out and regional(ch) and len(out[-1]) == 1 and regional(out[-1])
        if out and (_is_attached(ch) or out[-1].endswith("‍") or flag_pair):
            out[-1] += ch
        else:
            out.append(ch)
    return out


@lru_cache(maxsize=None)
def _cmap(path: str) -> frozenset[int]:
    with TTFont(path, lazy=True) as f:
        return frozenset(f.getBestCmap())


@lru_cache(maxsize=None)
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


@dataclass(frozen=True)
class FontStack:
    """Ordered font files; the first is the primary face."""

    files: tuple[str, ...]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(str(FONT_DIR / f) for f in self.files)

    def font_index_for(self, ch: str) -> int | None:
        """First font in the stack with a glyph for ch, or None if none has one."""
        cp = ord(ch)
        # Prefer the emoji font for pictographs even if a text font has a glyph.
        if cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF:
            for i, p in enumerate(self.paths):
                if "Emoji" in p and cp in _cmap(p):
                    return i
        for i, p in enumerate(self.paths):
            if cp in _cmap(p):
                return i
        return None

    def runs(self, text: str) -> list[tuple[str, int]]:
        """[(text, font_index)], merging neighbours that use the same font.

        Uncovered characters are dropped. A space stays in the surrounding run only when
        the text on both sides uses the same font (keeps Arabic phrases shaped as one
        RTL run); otherwise it uses the primary font, so emoji spacing stays normal and
        bidi reordering can't move it.
        """
        parts = self._substitute(clusters(text))
        idxs = [None if cl[0].isspace() else self.font_index_for(cl[0]) for cl in parts]
        out: list[tuple[str, int]] = []
        for k, cl in enumerate(parts):
            if cl[0].isspace():
                prev = out[-1][1] if out else None
                nxt = next((i for i, c in zip(idxs[k + 1:], parts[k + 1:])
                            if i is not None and not c[0].isspace()), None)
                keep = prev is not None and prev == nxt and ord(cl[0]) in _cmap(self.paths[prev])
                idx = prev if keep else 0
            else:
                idx = idxs[k]
                if idx is None:
                    continue
            if out and out[-1][1] == idx:
                out[-1] = (out[-1][0] + cl, idx)
            else:
                out.append((cl, idx))
        return out

    def _substitute(self, parts: list[str]) -> list[str]:
        """Swap undrawable stylised characters for plain ones where Unicode has an
        equivalent (NFKC): "𝓕𝓪𝓷𝓬𝔂" -> "Fancy", "Ⓦ" -> "W", "ﬁ" -> "fi"."""
        out: list[str] = []
        for cl in parts:
            if cl[0].isspace() or self.font_index_for(cl[0]) is not None:
                out.append(cl)
                continue
            alt = unicodedata.normalize("NFKC", cl)
            if alt != cl and all(c.isspace() or self.font_index_for(c) is not None for c in alt):
                out.extend(clusters(alt))
            else:
                out.append(cl)  # dropped later by runs()
        return out

    def legible(self, text: str) -> bool:
        """True if at least one letter or digit in text can be drawn."""
        return any(
            c[0].isalnum() and self.font_index_for(c[0]) is not None
            for c in self._substitute(clusters(clean(text)))
        )

    def font(self, index: int, size: int) -> ImageFont.FreeTypeFont:
        return _font(self.paths[index], size)

    def width(self, text: str, size: int) -> float:
        return sum(self.font(i, size).getlength(run) for run, i in self.runs(text))

    def draw(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        size: int,
        fill,
        anchor: str = "ls",
    ) -> float:
        """Draw text with its baseline at y. anchor: 'ls' left, 'rs' right, 'ms' centred.

        Returns the drawn width.
        """
        x, y = xy
        total = self.width(text, size)
        if anchor == "rs":
            x -= total
        elif anchor == "ms":
            x -= total / 2
        for run, i in self.runs(text):
            f = self.font(i, size)
            draw.text((x, y), run, font=f, fill=fill, anchor="ls")
            x += f.getlength(run)
        return total


def fit(
    text: str,
    stack: FontStack,
    max_width: float,
    size: int,
    min_size: int,
) -> tuple[str, int]:
    """Shrink the font down to min_size; if it still doesn't fit, truncate with an ellipsis."""
    text = clean(text)
    s = size
    while s > min_size and stack.width(text, s) > max_width:
        s -= 2
    s = max(s, min_size)
    if stack.width(text, s) <= max_width:
        return text, s
    parts = clusters(text)
    lo, hi = 0, len(parts)
    while lo < hi:  # longest prefix that fits with an ellipsis
        mid = (lo + hi + 1) // 2
        if stack.width("".join(parts[:mid]).rstrip() + ELLIPSIS, s) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return "".join(parts[:lo]).rstrip() + ELLIPSIS, s


# Display (team names, headings) and body stacks.
SCRIPTS_BOLD = (
    "NotoSansArabic-Bold.ttf",
    "NotoSansHebrew-Bold.ttf",
    "NotoSansDevanagari-Bold.ttf",
    "NotoSansThai-Bold.ttf",
    "NotoEmoji-Bold.ttf",
)
SCRIPTS_REGULAR = tuple(f.replace("-Bold", "-Regular") for f in SCRIPTS_BOLD)
# Subset to common characters, bold only (see scripts/build_fonts.py).
CJK = ("NotoSansCJK-Bold-subset.ttf", "NotoSansKR-Bold-subset.ttf")
SCRIPTS_BOLD += CJK
SCRIPTS_REGULAR += CJK

DISPLAY = FontStack(("SpaceGrotesk-Bold.ttf", "Inter-ExtraBold.ttf") + SCRIPTS_BOLD)
HEAVY = FontStack(("Inter-ExtraBold.ttf",) + SCRIPTS_BOLD)
LABEL = FontStack(("Inter-SemiBold.ttf",) + SCRIPTS_BOLD)
BODY = FontStack(("Inter-Regular.ttf",) + SCRIPTS_REGULAR)
