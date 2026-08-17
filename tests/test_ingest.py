"""WP1.2 — routing, registry, groups, the PDF chain, raster pass-through, gate.

Every fixture here is generated (tests/fixtures/make_captures.py) and tests
*plumbing only*. Nothing in this file says anything about what a model can read
off a capture; that is WP0.3, and it needs real material.
"""

import hashlib
import shutil

import make_captures as mk
import pytest

from knowledge_base import config
from knowledge_base.ingest import groups, pdfdoc, raster
from knowledge_base.ingest.exif import camera_tags, datetime_original
from knowledge_base.ingest.registry import Entry, Registry, sha256_of
from knowledge_base.ingest.resolution import gate, measure
from knowledge_base.ingest.route import RoutingError, route, source_key
from knowledge_base.ingest.sync import ingest_field
from knowledge_base.pipeline.queues import Queues

FIELD = "complex-analysis"


@pytest.fixture
def settings():
    return config.load(config.ROOT / "config.yaml")


@pytest.fixture
def inbox(tmp_path):
    d = tmp_path / "inbox" / FIELD
    (d / "Lecture-Boards").mkdir(parents=True)
    (d / "Texts" / "Brown & Churchill 9e").mkdir(parents=True)
    (d / "Texts" / "Unsorted").mkdir(parents=True)
    return d


# ── routing (§I-6.3) ──────────────────────────────────────────────────

def test_kind_comes_from_the_folder_never_from_the_image(inbox, settings):
    """The same bytes in two folders must route to two different kinds — this is
    what stops a photographed book page from inheriting the exam star."""
    board = mk.make_photo(inbox / "Lecture-Boards" / "a.jpg")
    text = inbox / "Texts" / "Brown & Churchill 9e" / "a.jpg"
    shutil.copyfile(board, text)
    assert sha256_of(board) == sha256_of(text)
    assert route(board, inbox, settings).kind.value == "board"
    assert route(text, inbox, settings).kind.value == "textbook"


def test_capture_comes_from_the_file(inbox, settings):
    photo = mk.make_photo(inbox / "Lecture-Boards" / "b.jpg")
    shot = mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "s.png")
    pdf = mk.make_pdf(inbox / "Texts" / "Brown & Churchill 9e" / "book.pdf")
    assert route(photo, inbox, settings).capture.value == "photo"
    assert route(shot, inbox, settings).capture.value == "raster"
    assert route(pdf, inbox, settings).capture.value == "pdf"


def test_unsorted_holds_source_null(inbox, settings):
    p = mk.make_screenshot(inbox / "Texts" / "Unsorted" / "x.png")
    r = route(p, inbox, settings)
    assert r.unsorted is True and r.source_key is None


def test_source_key_is_stable_across_punctuation_and_case():
    assert source_key("Brown & Churchill 9e") == "brown-churchill-9e"
    assert source_key("brown—churchill  9E") == source_key("Brown & Churchill 9e")


def test_files_outside_the_two_capture_folders_are_refused(inbox, settings):
    stray = mk.make_screenshot(inbox / "loose.png")
    with pytest.raises(RoutingError):
        route(stray, inbox, settings)


def test_filenames_are_never_parsed_for_routing(inbox, settings):
    """A screenshot named like a photo must still route as a raster."""
    p = mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "IMG_20260503_141507.png")
    assert route(p, inbox, settings).capture.value == "raster"


# ── EXIF ──────────────────────────────────────────────────────────────

def test_exif_round_trip(tmp_path):
    p = mk.make_photo(tmp_path / "p.jpg", make="Pixel", model="8a",
                      taken="2026:03:03 09:15:00")
    assert camera_tags(p)
    dt = datetime_original(p)
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 3, 3, 9)


def test_screenshot_has_no_camera_tags(tmp_path):
    assert not camera_tags(mk.make_screenshot(tmp_path / "s.png"))


# ── resolution gate (§I-6.3c) ─────────────────────────────────────────

def test_gate_measures_the_height_it_was_given(tmp_path):
    for h in (12, 30, 48):
        p = mk.make_page_image(tmp_path / f"h{h}.png", text_height_px=h)
        measured, n = measure(p)
        assert n > 10
        assert abs(measured - h) <= 1, f"expected ~{h}px, measured {measured}px"


def test_gate_passes_everything_while_the_floor_is_unmeasured(tmp_path):
    p = mk.make_page_image(tmp_path / "tiny.png", text_height_px=4)
    m = gate(p, floor_px=0)
    assert m.passes and not m.measured


def test_gate_rejects_below_a_measured_floor(tmp_path):
    small = mk.make_page_image(tmp_path / "small.png", text_height_px=8)
    big = mk.make_page_image(tmp_path / "big.png", text_height_px=40)
    assert gate(small, floor_px=20).passes is False
    assert gate(big, floor_px=20).passes is True


# ── raster chain (§I-6.3b) ────────────────────────────────────────────

def test_raster_staging_is_byte_identical(tmp_path):
    """Preprocessing is deliberately empty. Any transform here is a regression."""
    src = mk.make_screenshot(tmp_path / "shot.png", text_height_px=26)
    staged = raster.stage(src, "c1", tmp_path / "derived", floor_px=0)
    assert staged.path.read_bytes() == src.read_bytes()
    assert hashlib.sha256(staged.path.read_bytes()).hexdigest() == sha256_of(src)


# ── PDF chain (§I-6.4) ────────────────────────────────────────────────

def test_pdf_renders_pages_with_text_layer(tmp_path):
    pdf = mk.make_pdf(tmp_path / "b.pdf", pages=3)
    assert pdfdoc.info(pdf).page_count == 3
    pages = pdfdoc.render_pages(pdf, [1, 3], tmp_path / "out", dpi=150)
    assert [p.page for p in pages] == [1, 3]
    for p in pages:
        assert p.image.exists() and p.width > 500
        assert "domain" in p.text
    assert "page 3" in pages[1].text


def test_pdf_page_out_of_range_is_an_error(tmp_path):
    pdf = mk.make_pdf(tmp_path / "b.pdf", pages=2)
    with pytest.raises(ValueError):
        pdfdoc.render_pages(pdf, [5], tmp_path / "out")


# ── groups (§I-6.5) ───────────────────────────────────────────────────

def test_pdf_groups_are_contiguous_runs():
    assert groups.pdf_groups([1, 2, 3, 7, 8], "bc9e", 8) == [
        ("bc9e-pp1-3", [1, 2, 3]), ("bc9e-pp7-8", [7, 8])]
    assert [g for g, _ in groups.pdf_groups(list(range(1, 12)), "bc9e", 4)] == [
        "bc9e-pp1-4", "bc9e-pp5-8", "bc9e-pp9-11"]


def test_raster_group_is_one_per_drop():
    assert groups.raster_group("2026-08-04T10:00:00+00:00") == "drop-2026-08-04T10:00:00+00:00"


def test_dated_subfolder_wins(inbox, settings):
    (inbox / "Lecture-Boards" / "2026-05-03").mkdir()
    p = mk.make_photo(inbox / "Lecture-Boards" / "2026-05-03" / "a.jpg",
                      taken="2026:01:01 08:00:00")
    e = Entry(sha256="x", path="Lecture-Boards/2026-05-03/a.jpg", field_key=FIELD,
              kind="board", capture="photo", source_key=None, unsorted=False,
              size=1, mtime=0.0, first_seen="t")
    group, signal, warn = groups.resolve_board_group(e, p, settings)
    assert (group, signal, warn) == ("2026-05-03", groups.FOLDER, False)


def test_exif_beats_filename(inbox, settings):
    p = mk.make_photo(inbox / "Lecture-Boards" / "2020-01-01-mislabelled.jpg",
                      taken="2026:05:03 14:00:00")
    e = Entry(sha256="x", path="Lecture-Boards/2020-01-01-mislabelled.jpg", field_key=FIELD,
              kind="board", capture="photo", source_key=None, unsorted=False,
              size=1, mtime=0.0, first_seen="t")
    group, signal, _ = groups.resolve_board_group(e, p, settings)
    assert signal == groups.EXIF_DATE and group.startswith("2026-05-03")


def test_filename_date_is_step_three(inbox, settings):
    p = mk.make_screenshot(inbox / "Lecture-Boards" / "2026-04-07-board-2.png")
    e = Entry(sha256="x", path="Lecture-Boards/2026-04-07-board-2.png", field_key=FIELD,
              kind="board", capture="photo", source_key=None, unsorted=False,
              size=1, mtime=0.0, first_seen="t")
    group, signal, warn = groups.resolve_board_group(e, p, settings)
    assert (group, signal, warn) == ("2026-04-07", groups.FILENAME, False)


def test_file_timestamp_is_last_and_warns(inbox, settings):
    p = mk.make_screenshot(inbox / "Lecture-Boards" / "board.png")
    e = Entry(sha256="x", path="Lecture-Boards/board.png", field_key=FIELD,
              kind="board", capture="photo", source_key=None, unsorted=False,
              size=1, mtime=p.stat().st_mtime, first_seen="t")
    _, signal, warn = groups.resolve_board_group(e, p, settings)
    assert signal == groups.FILE_MTIME and warn is True


def test_a_serial_number_is_not_read_as_a_date():
    assert groups.date_in_name("DSC20260504321.jpg") is None
    assert groups.date_in_name("2026-05-03-b1.jpg") is not None


def test_session_identity_is_resolved_once_and_never_regrouped(tmp_path):
    """A26. Re-deriving would silently regroup years-old captures."""
    reg = Registry(tmp_path)
    reg.entries["h"] = Entry(sha256="h", path="Lecture-Boards/a.jpg", field_key=FIELD,
                             kind="board", capture="photo", source_key=None, unsorted=False,
                             size=1, mtime=0.0, first_seen="t")
    reg.set_group("h", "2026-05-03", groups.EXIF_DATE)
    reg.set_group("h", "2026-09-09", groups.FILE_MTIME)
    assert reg.entries["h"].group == "2026-05-03"
    assert reg.entries["h"].group_signal == groups.EXIF_DATE


def test_five_lectures_in_one_upload_do_not_merge(inbox, settings):
    """The real defect from docs/FINDINGS.md, "Session grouping and volume": one upload
    batch delivered five lectures inside fifteen minutes. Upload time cannot
    separate them; EXIF capture time can."""
    peers, made = [], []
    for i, hour in enumerate((9, 9, 11, 11, 15)):
        p = mk.make_photo(inbox / "Lecture-Boards" / f"b{i}.jpg",
                          taken=f"2026:04:07 {hour:02d}:0{i}:00")
        e = Entry(sha256=f"h{i}", path=f"Lecture-Boards/b{i}.jpg", field_key=FIELD,
                  kind="board", capture="photo", source_key=None, unsorted=False,
                  size=1, mtime=0.0, first_seen="same-upload",
                  exif={"DateTimeOriginal": f"2026:04:07 {hour:02d}:0{i}:00"})
        peers.append(e)
        made.append((e, p))
    assigned = {groups.resolve_board_group(e, p, settings, peers=peers)[0] for e, p in made}
    assert len(assigned) == 3, f"expected three sessions, got {assigned}"


# ── the driver end to end ─────────────────────────────────────────────

def test_ingest_records_routes_groups_and_queues(tmp_path, inbox, settings):
    mk.make_pdf(inbox / "Texts" / "Brown & Churchill 9e" / "bc.pdf")
    mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "s1.png", text_height_px=28)
    # A different height, so the two screenshots are different bytes. Identical
    # bytes in two folders are one capture by design (§I-6.2) — see the
    # dedicated test below.
    mk.make_screenshot(inbox / "Texts" / "Unsorted" / "u1.png", text_height_px=22)
    mk.make_photo(inbox / "Lecture-Boards" / "b1.jpg", taken="2026:05:03 14:00:00")

    r = ingest_field(FIELD, settings, tmp_path)
    assert r.new == 4 and r.grouped == 4
    q = Queues(tmp_path).counts()
    assert q["unsorted-source"] == 1, "A25: one entry per drop, not one per file"
    assert q["new-source"] == 1

    reg = Registry(tmp_path)
    by_path = {e.path: e for e in reg.by_field(FIELD)}
    assert by_path["Texts/Brown & Churchill 9e/bc.pdf"].capture == "pdf"
    assert by_path["Texts/Unsorted/u1.png"].source_key is None
    assert by_path["Lecture-Boards/b1.jpg"].group.startswith("2026-05-03")
    assert by_path["Texts/Brown & Churchill 9e/s1.png"].group.startswith("drop-")


def test_identical_bytes_are_one_capture(tmp_path, inbox, settings):
    """§I-6.2: identical hashes are never reprocessed, wherever they sit. The
    same page captured on two devices yields different bytes and is caught later,
    at item level, by canonical-hash dedup — that is the expected path."""
    a = mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "a.png")
    shutil.copyfile(a, inbox / "Texts" / "Unsorted" / "copy.png")
    r = ingest_field(FIELD, settings, tmp_path)
    assert (r.seen, r.new) == (2, 1)


def test_hashing_makes_ingest_idempotent(tmp_path, inbox, settings):
    mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "s1.png")
    first = ingest_field(FIELD, settings, tmp_path)
    second = ingest_field(FIELD, settings, tmp_path)
    assert (first.new, second.new) == (1, 0)
    assert second.skipped_known == 1


def test_group_assignment_ignores_filename_and_mtime_for_rasters(tmp_path, inbox, settings):
    """A drop of screenshots in arbitrary order must group as one drop."""
    import os
    d = inbox / "Texts" / "Brown & Churchill 9e"
    for i, name in enumerate(("zzz.png", "aaa.png", "mmm.png")):
        p = mk.make_screenshot(d / name, text_height_px=20 + i)
        os.utime(p, (1_000_000 * (i + 1), 1_000_000 * (i + 1)))
    ingest_field(FIELD, settings, tmp_path)
    reg = Registry(tmp_path)
    rasters = [e for e in reg.by_field(FIELD) if e.capture == "raster"]
    assert len({e.group for e in rasters}) == 1


def test_low_resolution_routes_to_review_when_the_floor_is_set(tmp_path, inbox, settings):
    mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "blurry.png",
                       text_height_px=6)
    measured = settings.model_copy(update={"resolution_floor_px": 20})
    r = ingest_field(FIELD, measured, tmp_path)
    assert r.low_resolution
    assert Queues(tmp_path).counts()["low-resolution"] == 1


def test_unroutable_files_are_reported_not_discarded(tmp_path, inbox, settings):
    mk.make_screenshot(inbox / "loose.png")
    r = ingest_field(FIELD, settings, tmp_path)
    assert r.unrouted == ["loose.png"]
    assert (inbox / "loose.png").exists(), "originals are immutable"
