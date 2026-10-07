"""Artifact lifecycle (Sprint 9.8 / 4.16).

    Generated -> Registered -> Validated -> Stored -> Available -> Archived

An artifact becomes immutable once it is registered: its type, location, size
and checksum never change again, and only its lifecycle status advances --
always forward, always along this path. This module holds the transition table
and the guard that enforces it; it performs no persistence.

The states describe what is true of the artifact:

    Generated   the bytes have been written by the stage that produced them
    Registered  a registry entry exists, with measured size and checksum
    Validated   the stored bytes have been re-verified against the registry
    Stored      the artifact is confirmed present in the artifact store
    Available   the artifact is released for download
    Archived    the artifact is retained but no longer offered
"""

from __future__ import annotations

from collections.abc import Mapping

from app.reporting.constants import ArtifactStatus
from app.reporting.exceptions import InvalidArtifactTransitionError

#: The lifecycle, in order. An artifact only ever moves forward along it.
LIFECYCLE_ORDER: tuple[ArtifactStatus, ...] = (
    ArtifactStatus.GENERATED,
    ArtifactStatus.REGISTERED,
    ArtifactStatus.VALIDATED,
    ArtifactStatus.STORED,
    ArtifactStatus.AVAILABLE,
    ArtifactStatus.ARCHIVED,
)

ALLOWED_ARTIFACT_TRANSITIONS: Mapping[ArtifactStatus, frozenset[ArtifactStatus]] = {
    status: frozenset({LIFECYCLE_ORDER[index + 1]}) if index + 1 < len(LIFECYCLE_ORDER) else frozenset()
    for index, status in enumerate(LIFECYCLE_ORDER)
}


class ArtifactLifecycle:
    """Guards every lifecycle transition of a report artifact."""

    @staticmethod
    def is_final(status: ArtifactStatus) -> bool:
        """True once the artifact can advance no further."""
        return not ALLOWED_ARTIFACT_TRANSITIONS[status]

    @staticmethod
    def can_transition(current: ArtifactStatus, target: ArtifactStatus) -> bool:
        """Whether ``target`` is the state that legally follows ``current``."""
        return target in ALLOWED_ARTIFACT_TRANSITIONS[current]

    @classmethod
    def validate(cls, current: ArtifactStatus, target: ArtifactStatus) -> None:
        """Raises ``InvalidArtifactTransitionError`` unless the step is legal."""
        if not cls.can_transition(current, target):
            raise InvalidArtifactTransitionError(
                f"A report artifact may not move from {current.value} to {target.value}"
            )

    @classmethod
    def path(cls, current: ArtifactStatus, target: ArtifactStatus) -> tuple[ArtifactStatus, ...]:
        """The lifecycle steps taking an artifact from ``current`` to ``target``.

        Every intermediate step is validated, so advancing several states at
        once can never skip a state that does not exist on the path or move an
        artifact backwards.
        """
        if current is target:
            return ()
        if LIFECYCLE_ORDER.index(target) < LIFECYCLE_ORDER.index(current):
            raise InvalidArtifactTransitionError(
                f"A report artifact may not move backwards from {current.value} to {target.value}"
            )

        steps: list[ArtifactStatus] = []
        position = current
        while position is not target:
            following = next(iter(ALLOWED_ARTIFACT_TRANSITIONS[position]))
            cls.validate(position, following)
            steps.append(following)
            position = following
        return tuple(steps)
