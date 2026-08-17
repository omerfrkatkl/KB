"""The PDF chain (§I-6.4).

Per page: a 300 dpi render, the born-digital text layer, and lossless extraction
of the embedded images.

The render is what the model reads and is **ground truth**. The text layer
accompanies it in the prompt as a transcription aid, never as a replacement: a
PDF's text layer routinely loses the very things the pipeline cares about —
subscript positions, integral bounds, and anything set as a figure — and it
carries no layout, so it cannot support the region coordinates that `coverage`
and figure bboxes are expressed in.

Embedded images are extracted losslessly rather than cropped from the render,
because a figure re-rasterised at 300 dpi and then cropped is strictly worse than
the original the publisher embedded (§I-11 figure fidelity).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf

from knowledge_base.ops.log import get

log = get("pdfdoc")

RENDER_DPI = 300


@dataclass
class PageRender:
    page: int                      # 1-based, as a human cites it
    image: Path
    width: int
    height: int
    text: str
    images: list[Path] = field(default_factory=list)


@dataclass
class DocumentInfo:
    page_count: int
    title: str | None
    toc: list[tuple[int, str, int]]   # (level, title, page) — feeds the ToC proposal


def info(pdf: Path) -> DocumentInfo:
    with fitz.open(pdf) as doc:
        meta = doc.metadata or {}
        return DocumentInfo(
            page_count=doc.page_count,
            title=(meta.get("title") or "").strip() or None,
            toc=[(lvl, title.strip(), page) for lvl, title, page in doc.get_toc()],
        )


def render_pages(
    pdf: Path, pages: list[int], out_dir: Path, dpi: int = RENDER_DPI,
    extract_images: bool = True,
) -> list[PageRender]:
    """Render 1-based `pages` of `pdf` into `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    out: list[PageRender] = []

    with fitz.open(pdf) as doc:
        for number in pages:
            if not 1 <= number <= doc.page_count:
                raise ValueError(f"{pdf.name}: page {number} is outside 1..{doc.page_count}")
            page = doc.load_page(number - 1)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = out_dir / f"p{number:04d}.png"
            pix.save(image)

            embedded: list[Path] = []
            if extract_images:
                embedded = _extract_embedded(doc, page, number, out_dir)

            out.append(PageRender(page=number, image=image, width=pix.width,
                                  height=pix.height, text=page.get_text("text"),
                                  images=embedded))
    return out


def _extract_embedded(doc, page, number: int, out_dir: Path) -> list[Path]:
    """Lossless embedded-image extraction, in the publisher's own encoding."""
    saved: list[Path] = []
    for index, meta in enumerate(page.get_images(full=True), start=1):
        xref = meta[0]
        try:
            raw = doc.extract_image(xref)
        except (RuntimeError, ValueError) as e:      # a damaged or exotic stream
            log.warning("page %d image %d not extractable: %s", number, index, e)
            continue
        dest = out_dir / f"p{number:04d}-img{index:02d}.{raw['ext']}"
        dest.write_bytes(raw["image"])
        saved.append(dest)
    return saved


def page_numbers(pdf: Path) -> list[int]:
    with fitz.open(pdf) as doc:
        return list(range(1, doc.page_count + 1))
