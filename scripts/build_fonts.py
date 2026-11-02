"""Build the static font files in app/assets/fonts/ from Google Fonts variable fonts.

Only needed if you want to change weights or add a script. Sources (OFL) come from
https://github.com/google/fonts/tree/main/ofl:

    spacegrotesk/SpaceGrotesk[wght].ttf      inter/Inter[opsz,wght].ttf
    notosansarabic/NotoSansArabic[wdth,wght].ttf   notosanshebrew/...  notosansdevanagari/...
    notosansthai/NotoSansThai[wdth,wght].ttf       notoemoji/NotoEmoji[wght].ttf
    notosanssc/NotoSansSC[wght].ttf                notosanskr/NotoSansKR[wght].ttf

Download them into a folder with the short names used below, then run:

    python -m scripts.build_fonts <source_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).resolve().parent.parent / "app" / "assets" / "fonts"

# (source file, output name, axis locations)
INSTANCES = [
    ("SpaceGrotesk.ttf", "SpaceGrotesk-Bold.ttf", {"wght": 700}),
    ("Inter.ttf", "Inter-Regular.ttf", {"wght": 400, "opsz": 28}),
    ("Inter.ttf", "Inter-SemiBold.ttf", {"wght": 600, "opsz": 28}),
    ("Inter.ttf", "Inter-ExtraBold.ttf", {"wght": 800, "opsz": 32}),
    ("NotoSansArabic.ttf", "NotoSansArabic-Regular.ttf", {"wght": 400, "wdth": 100}),
    ("NotoSansArabic.ttf", "NotoSansArabic-Bold.ttf", {"wght": 700, "wdth": 100}),
    ("NotoSansHebrew.ttf", "NotoSansHebrew-Regular.ttf", {"wght": 400, "wdth": 100}),
    ("NotoSansHebrew.ttf", "NotoSansHebrew-Bold.ttf", {"wght": 700, "wdth": 100}),
    ("NotoSansDevanagari.ttf", "NotoSansDevanagari-Regular.ttf", {"wght": 400, "wdth": 100}),
    ("NotoSansDevanagari.ttf", "NotoSansDevanagari-Bold.ttf", {"wght": 700, "wdth": 100}),
    ("NotoSansThai.ttf", "NotoSansThai-Regular.ttf", {"wght": 400, "wdth": 100}),
    ("NotoSansThai.ttf", "NotoSansThai-Bold.ttf", {"wght": 700, "wdth": 100}),
    ("NotoEmoji.ttf", "NotoEmoji-Regular.ttf", {"wght": 400}),
    ("NotoEmoji.ttf", "NotoEmoji-Bold.ttf", {"wght": 700}),
]


def _euc_block(codec: str, rows: range) -> set[int]:
    """Characters of a double-byte national charset, by row (e.g. GB2312 level 1)."""
    out = set()
    for hi in rows:
        for lo in range(0xA1, 0xFF):
            try:
                out.add(ord(bytes([hi, lo]).decode(codec)))
            except UnicodeDecodeError:
                pass
    return out


def _ranges(*pairs: tuple[int, int]) -> set[int]:
    return {cp for a, b in pairs for cp in range(a, b + 1)}


def cjk_chars() -> set[int]:
    """Common Chinese (GB2312 level 1) + Japanese (JIS level 1 kanji, all kana) + punctuation."""
    return (
        _euc_block("gb2312", range(0xB0, 0xD8))
        | _euc_block("euc_jp", range(0xB0, 0xD0))
        | _ranges((0x20, 0x7E), (0x3000, 0x303F), (0x3040, 0x30FF), (0x31F0, 0x31FF),
                  (0xFF00, 0xFFEF))
    )


def hangul_chars() -> set[int]:
    """The 2,350 common Hangul syllables of KS X 1001, plus compatibility jamo."""
    return _euc_block("euc_kr", range(0xB0, 0xC9)) | _ranges((0x20, 0x7E), (0x3130, 0x318F))


# (source, output, axis location, characters to keep) - bold only, subset to keep size down
CJK = [
    ("NotoSansSC.ttf", "NotoSansCJK-Bold-subset.ttf", {"wght": 700}, cjk_chars),
    ("NotoSansKR.ttf", "NotoSansKR-Bold-subset.ttf", {"wght": 700}, hangul_chars),
]


def main(src: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for source, name, loc in INSTANCES:
        font = TTFont(src / source)
        axes = {a.axisTag for a in font["fvar"].axes}
        static = instancer.instantiateVariableFont(
            font, {k: v for k, v in loc.items() if k in axes}, updateFontNames=False
        )
        static.save(OUT / name)
        print(f"{name:34} {(OUT / name).stat().st_size // 1024:>5} KB")
    for source, name, loc, chars in CJK:
        font = instancer.instantiateVariableFont(TTFont(src / source), loc)
        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=chars())
        sub.subset(font)
        font.save(OUT / name)
        print(f"{name:34} {(OUT / name).stat().st_size // 1024:>5} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.build_fonts <source_dir>")
    main(Path(sys.argv[1]))
