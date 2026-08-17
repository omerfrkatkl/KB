"""Settings — the typed view of `config.yaml`.

Every tunable in this system lives in one file so that a measurement taken in
Phase 0 lands in exactly one place and every stage reads the same number. The
model is strict: an unknown key is an error, because a silently ignored setting
is indistinguishable from a setting that was never applied.

Values documented as "measured" (`budget.max_pages_per_night`,
`resolution_floor_px`) default to 0, which every consumer reads as *unset*. That
is deliberate — a plausible-looking guess would be indistinguishable from a
measurement, and the plan is explicit that these come from WP0.3/WP0.4.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config.yaml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FieldConfig(_Strict):
    title: str
    captures: str  # Drive-relative path to this field's capture folder


class CaptureFolders(_Strict):
    board: str = "Lecture-Boards"
    textbook: str = "Texts"
    unsorted: str = "Texts/Unsorted"


class Budget(_Strict):
    max_pages_per_night: int = 0  # 0 = unmeasured (WP0.4 / B3)


class Batching(_Strict):
    pdf_pages: int = 8
    board_crops: int = 6
    raster_captures: int = 6


class Groups(_Strict):
    session_gap_minutes: int = 45  # board x photo only (I-6.5)


class Dedup(_Strict):
    auto_confirm: float = 0.93
    queue_floor: float = 0.75


class Settings(_Strict):
    drive_remote: str = "gdrive"
    drive_root: str = "Mathematics"
    fields: dict[str, FieldConfig]
    inactive_subjects: list[str] = Field(default_factory=list)
    capture_folders: CaptureFolders = CaptureFolders()
    output_folder: str
    reports_folder: str
    budget: Budget = Budget()
    batching: Batching = Batching()
    groups: Groups = Groups()
    resolution_floor_px: int = 0  # 0 = unmeasured (WP0.3 / B16)
    dedup: Dedup = Dedup()
    dialect: str = "typst"
    model: str = "default"

    # ---- derived paths -------------------------------------------------
    # Kept out of the model proper: they are functions of the repository
    # location, not of the file, and must not round-trip into YAML.

    def field_names(self) -> list[str]:
        return sorted(self.fields)

    def inbox(self, field: str, root: Path = ROOT) -> Path:
        return root / "inbox" / field

    def derived(self, field: str, root: Path = ROOT) -> Path:
        return root / "derived" / field

    def field_dir(self, field: str, root: Path = ROOT) -> Path:
        return root / "fields" / field

    def measured(self) -> dict[str, bool]:
        """Which Phase-0 measurements have landed. Consumers gate on this."""
        return {
            "budget.max_pages_per_night": self.budget.max_pages_per_night > 0,
            "resolution_floor_px": self.resolution_floor_px > 0,
        }


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    return y


def load(path: Path | str = DEFAULT_CONFIG) -> Settings:
    path = Path(path)
    data = _yaml().load(path.read_text())
    return Settings.model_validate(_plain(data))


def dump(settings: Settings, path: Path | str) -> None:
    """Write settings back. Used by the Phase-0 spikes to record measurements."""
    with Path(path).open("w") as fh:
        _yaml().dump(settings.model_dump(mode="json"), fh)


def _plain(obj):
    """ruamel returns CommentedMap/CommentedSeq; pydantic wants plain types."""
    if hasattr(obj, "items"):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


@lru_cache(maxsize=1)
def settings() -> Settings:
    return load()
