from __future__ import annotations
from typing import Callable
from ..runtime.types import OperationalFrameContract, QualificationState

FrameInvalidationCallback = Callable[[str, int, str], None]


class OperationalFrameRegistry:
    """Currentness registry for externally qualified operational frames.

    MS895 showed that capability candidates could outlive the sensorimotor frame
    that generated their traces because v0.3 had no content-bound frame epoch.
    This registry makes frame currentness explicit without claiming Microseed can
    yet construct or self-qualify the frame.
    """

    def __init__(self, *, on_invalidate: FrameInvalidationCallback | None = None):
        self.frames: dict[str, OperationalFrameContract] = {}
        self.epochs: dict[str, int] = {}
        self.capability_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, frame: OperationalFrameContract) -> None:
        if frame.frame_id in self.frames:
            raise ValueError(f"duplicate operational frame: {frame.frame_id}")
        if frame.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            raise ValueError("operational frame must be externally qualified before registration")
        if not frame.signature_sha256:
            raise ValueError("operational frame requires content-bound signature_sha256")
        self.frames[frame.frame_id] = frame
        self.epochs[frame.frame_id] = 0

    def bind_capability(self, frame_id: str, capability_id: str) -> None:
        if frame_id not in self.frames:
            raise ValueError(f"unknown operational frame: {frame_id}")
        self.capability_dependents.setdefault(frame_id, set()).add(capability_id)

    def is_current(self, frame_id: str, epoch: int | None = None) -> bool:
        frame = self.frames.get(frame_id)
        if frame is None or frame.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            return False
        if epoch is not None and self.epochs.get(frame_id, -1) != int(epoch):
            return False
        return True

    def change(self, frame_id: str, *, reason: str = "FRAME_RELATION_CHANGED") -> int:
        if frame_id not in self.frames:
            raise ValueError(f"unknown operational frame: {frame_id}")
        self.epochs[frame_id] = self.epochs.get(frame_id, 0) + 1
        frame = self.frames[frame_id]
        frame.qualification = QualificationState.STALE
        frame.currentness = "STALE"
        if self._on_invalidate is not None:
            self._on_invalidate(frame_id, self.epochs[frame_id], reason)
        return self.epochs[frame_id]

    def snapshot(self) -> dict[str, dict]:
        return {
            fid: {
                "contract": frame.serializable(),
                "epoch": self.epochs.get(fid, 0),
                "capability_dependents": sorted(self.capability_dependents.get(fid, ())),
            }
            for fid, frame in sorted(self.frames.items())
        }
