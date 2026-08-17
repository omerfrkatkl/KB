"""Phase 3 code — photo chain, continuation, figures, audit.

**Read the photo tests carefully for what they do not claim.** The fixtures are
programmatically drawn quadrilaterals: they prove the warp arithmetic, the area
and aspect filters, and the edge-clipping rule behave as written. They say
nothing about whether a real board photograph detects, which is B11 and needs the
owner's 200 photographs (WP0.3). `docs/SLICE-FINDINGS.md` records what it cost
the last time generated material was read as evidence.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from knowledge_base.extract.contract import Audit
from knowledge_base.ingest import photo
from knowledge_base.models import item as M
from knowledge_base.models.profile import load_profile
from knowledge_base.pipeline import audit as audit_stage
from knowledge_base.pipeline import continuation, figures
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"


@pytest.fixture(scope="module")
def profile():
    return load_profile(FIELD, ROOT)


# ── geometric fixtures (NOT captures) ─────────────────────────────────

def scene(quads, size=(900, 1400), background=40):
    """A dark frame with light quadrilaterals drawn on it."""
    img = np.full((size[0], size[1], 3), background, np.uint8)
    for quad in quads:
        cv2.fillPoly(img, [np.array(quad, np.int32)], (210, 210, 205))
        cv2.polylines(img, [np.array(quad, np.int32)], True, (255, 255, 255), 3)
    return img


def write(tmp_path, name, image):
    path = tmp_path / name
    cv2.imwrite(str(path), image)
    return path


# ── quad detection (§I-6.3a) ──────────────────────────────────────────

def test_a_fully_visible_quad_is_detected(tmp_path):
    quad = [(200, 150), (1150, 180), (1120, 700), (230, 660)]
    quads, clipped = photo.detect_quads(scene([quad]))
    assert len(quads) == 1 and clipped == 0


def test_an_edge_clipped_quad_is_discarded_not_cropped(tmp_path):
    """A board running off the frame would otherwise yield a crop that looks
    complete and is not."""
    clipped_quad = [(-50, 150), (600, 170), (580, 700), (-40, 660)]
    quads, clipped = photo.detect_quads(scene([clipped_quad]))
    assert quads == [] and clipped >= 1


def test_two_boards_in_one_frame_both_detect(tmp_path):
    a = [(80, 120), (620, 140), (600, 560), (100, 540)]
    b = [(760, 130), (1300, 150), (1280, 570), (780, 550)]
    quads, _ = photo.detect_quads(scene([a, b]))
    assert len(quads) == 2, "a second board is content, not noise"


def test_a_tiny_region_is_not_a_board(tmp_path):
    quads, _ = photo.detect_quads(scene([[(50, 50), (140, 52), (138, 110), (48, 108)]]))
    assert quads == []


def test_an_extreme_aspect_ratio_is_rejected(tmp_path):
    strip = [(100, 400), (1300, 402), (1300, 430), (100, 428)]
    quads, _ = photo.detect_quads(scene([strip]))
    assert quads == []


def test_warp_rectifies_a_perspective_quad():
    quad = np.array([[100, 100], [500, 130], [480, 400], [120, 370]], np.float32)
    out = photo.warp(scene([quad.astype(int).tolist()]), quad)
    assert out.shape[0] > 200 and out.shape[1] > 300


def test_orientation_is_applied_before_geometry():
    img = np.zeros((100, 200, 3), np.uint8)
    assert photo.apply_orientation(img, 6).shape[:2] == (200, 100)
    assert photo.apply_orientation(img, 1).shape[:2] == (100, 200)


def test_no_confident_quad_falls_back_to_the_whole_image(tmp_path):
    """A photo that produced no crop is still material."""
    noise = np.random.default_rng(4).integers(0, 60, (600, 800, 3), dtype=np.uint8)
    result = photo.process(write(tmp_path, "noise.png", noise), tmp_path / "out")
    assert result.fell_back and result.flagged
    assert len(result.crops) == 1 and result.crops[0].path.exists()


def test_process_writes_crops_and_leaves_the_original_alone(tmp_path):
    quad = [(200, 150), (1150, 180), (1120, 700), (230, 660)]
    src = write(tmp_path, "board.png", scene([quad]))
    before = src.read_bytes()
    result = photo.process(src, tmp_path / "derived")
    assert not result.fell_back
    assert all(c.path.exists() for c in result.crops)
    assert src.read_bytes() == before, "originals are immutable"


def test_enhance_preserves_shape():
    img = scene([[(100, 100), (600, 110), (590, 400), (110, 390)]])
    assert photo.enhance(img).shape == img.shape


# ── continuation (§I-7.3) ─────────────────────────────────────────────

def open_theorem(**kw):
    return M.make(field=FIELD, type="theorem", status="open", slots=dict(
        citation_form="a bounded entire function is constant",
        hypotheses=["$f$ is entire"], conclusion="$f$ is constant",
        proofs=[dict(method="direct", steps=[
            dict(claim="$f'(z) = 0$", justification=dict(kind="by-computation"))])]),
        **kw)


class Frag:
    def __init__(self, continues, payload):
        self.continues, self.payload = continues, payload


def test_a_fragment_completes_an_open_item(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    parent = open_theorem()
    store.put(parent)
    report = continuation.apply_fragments(
        [Frag(parent.id, {"proofs": [{"conclusion": "$f$ is constant"}]})],
        store, profile, queues)
    assert report.merged == [parent.id]
    assert store.get(parent.id).slots["proofs"][0]["conclusion"] == "$f$ is constant"
    assert store.get(parent.id).status.value == "active"


def test_a_fragment_never_overwrites_a_filled_slot(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    parent = open_theorem()
    store.put(parent)
    continuation.apply_fragments(
        [Frag(parent.id, {"conclusion": "a worse second reading"})],
        store, profile, queues)
    assert store.get(parent.id).slots["conclusion"] == "$f$ is constant"


def test_a_fragment_appends_steps_rather_than_replacing_them(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    parent = open_theorem()
    store.put(parent)
    continuation.apply_fragments([Frag(parent.id, {"proofs": [{
        "conclusion": "$f$ is constant",
        "steps": [{"claim": "$f$ is bounded",
                   "justification": {"kind": "by-hypothesis"}}]}]})],
        store, profile, queues)
    steps = store.get(parent.id).slots["proofs"][0]["steps"]
    assert len(steps) == 2 and steps[0]["claim"] == "$f'(z) = 0$"


def test_a_fragment_naming_nothing_is_kept_for_review(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    report = continuation.apply_fragments(
        [Frag("01J9XA5T7K3M2N8P4Q6R9S0TVA", {"conclusion": "orphan"})],
        store, profile, queues)
    assert report.unmatched and queues.counts()["unclassified"] == 1
    assert queues.list("unclassified")[0].payload["payload"]["conclusion"] == "orphan"


def test_an_item_still_open_stays_open(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    parent = open_theorem()
    store.put(parent)
    report = continuation.apply_fragments(
        [Frag(parent.id, {"proofs": [{"steps": [
            {"claim": "$f$ is bounded", "justification": {"kind": "by-hypothesis"}}]}]})],
        store, profile, queues)
    assert report.still_open == [parent.id]


def test_open_items_that_go_quiet_are_queued_never_closed(tmp_path):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    stale = open_theorem(updated=M.datetime(2020, 1, 1, tzinfo=M.timezone.utc))
    store.put(stale)
    quiet = continuation.sweep_quiet(store, queues, days=21)
    assert quiet == [stale.id]
    assert queues.counts()["open-gone-quiet"] == 1
    assert store.get(stale.id).status.value == "open", "never closed automatically"


# ── figures (WP3.3) ───────────────────────────────────────────────────

def test_a_crop_is_padded_and_clamped_to_the_capture(tmp_path):
    src = write(tmp_path, "page.png", np.full((400, 600, 3), 255, np.uint8))
    crop = figures.crop_region(src, [10, 10, 100, 80], tmp_path / "fig.png")
    assert crop.path.exists()
    image = cv2.imread(str(crop.path))
    assert image.shape[0] > 80 and image.shape[1] > 100, "padding applied"
    edge = figures.crop_region(src, [0, 0, 50, 50], tmp_path / "edge.png")
    assert edge.bbox[0] == 0 and edge.bbox[1] == 0, "clamped, not negative"


def test_an_empty_crop_is_an_error_not_a_blank_image(tmp_path):
    src = write(tmp_path, "page.png", np.full((100, 100, 3), 255, np.uint8))
    with pytest.raises(ValueError):
        figures.crop_region(src, [500, 500, 10, 10], tmp_path / "x.png")


def test_an_embedded_image_is_preferred_when_the_aspect_matches(tmp_path):
    wide = write(tmp_path, "wide.png", np.full((100, 300, 3), 200, np.uint8))
    tall = write(tmp_path, "tall.png", np.full((300, 100, 3), 200, np.uint8))
    assert figures.pick_embedded([wide, tall], [0, 0, 300, 100]) == wide
    assert figures.pick_embedded([tall], [0, 0, 300, 100]) is None


def test_every_figure_passes_the_review_gate(tmp_path):
    queues = Queues(tmp_path)
    src = write(tmp_path, "p.png", np.full((300, 300, 3), 255, np.uint8))
    crop = figures.crop_region(src, [10, 10, 50, 50], tmp_path / "f.png")
    item = M.make(field=FIELD, type="remark", slots=dict(body="see the figure"))
    figures.queue_for_review(item, crop, "c1", queues)
    assert queues.counts()["figure-crop"] == 1
    assert item.figures == [], "attached only after the gate"


def test_attach_records_where_the_figure_came_from():
    item = M.make(field=FIELD, type="remark", slots=dict(body="x"),
                  provenance=[dict(kind="textbook", capture="pdf", page=3)])
    out = figures.attach(item, "fig-1.png", 0, [10, 10, 50, 50])
    assert out.figures[0].origin.provenance_index == 0


# ── the audit stage (§I-9) ────────────────────────────────────────────

def test_both_arrays_empty_is_a_pass(tmp_path):
    report = audit_stage.handle(Audit(), "b1", Queues(tmp_path))
    assert report.passed and not report.re_extract_regions


def test_a_gap_triggers_one_targeted_re_extraction(tmp_path):
    a = Audit(gaps=[{"capture_id": "c1", "region": [0, 0, 10, 10],
                     "description": "a definition of `region` was not extracted"}])
    report = audit_stage.handle(a, "b1", Queues(tmp_path))
    assert not report.passed and len(report.re_extract_regions) == 1


def test_an_exclusion_violation_is_treated_like_a_gap(tmp_path):
    """Exclusions are audited, never trusted: a skipped region is invisible
    downstream, because the item simply is not there."""
    a = Audit(exclusion_violations=[
        {"capture_id": "c1", "reason": "skipped as worked-demonstration, but it "
                                       "establishes that the converse fails"}])
    report = audit_stage.handle(a, "b1", Queues(tmp_path))
    assert report.violations == 1 and report.re_extract_regions


def test_a_second_failure_goes_to_a_human_rather_than_looping(tmp_path):
    queues = Queues(tmp_path)
    a = Audit(gaps=[{"capture_id": "c1", "description": "still missing"}])
    report = audit_stage.handle(a, "b1", queues, already_retried=True)
    assert not report.re_extract_regions
    assert queues.counts()["audit-gap"] == 1


def test_spotcheck_samples_items_with_their_source(tmp_path):
    store = Store(FIELD, tmp_path)
    for i in range(8):
        store.put(M.make(field=FIELD, type="remark", slots=dict(body=f"fact {i}"),
                         provenance=[dict(source="bc9e", kind="textbook",
                                          capture="pdf", page=i + 1,
                                          extractor=dict(prompt_hash="abc"))]))
    sample = audit_stage.spotcheck(store, count=3, seed=1)
    assert len(sample) == 3
    assert all(s["source"] == "bc9e" and s["prompt_hash"] == "abc" for s in sample)
    assert audit_stage.spotcheck(store, count=3, seed=1) == sample, "seeded, repeatable"
