"""Typed errors for founder-fit capability matching."""


class CapabilityMatchError(Exception):
    """Base error for capability match scoring."""


class UnknownFingerprintError(CapabilityMatchError):
    """Raised when a fingerprint is not present in the requirement matrix."""

    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        super().__init__(f"fingerprint not found in requirement matrix: {fingerprint}")


class UnknownCapabilityFamilyError(CapabilityMatchError):
    """Raised when a capability profile references an unapproved family."""

    def __init__(self, family: str) -> None:
        self.family = family
        super().__init__(f"unknown capability family: {family}")


class MissingCapabilityScoreError(CapabilityMatchError):
    """Raised when a required family level is absent from the profile."""

    def __init__(self, family: str) -> None:
        self.family = family
        super().__init__(f"missing capability score for family: {family}")


class InvalidCapabilityLevelError(CapabilityMatchError):
    """Raised when a capability level is outside the 0–100 range."""

    def __init__(self, family: str, level: int) -> None:
        self.family = family
        self.level = level
        super().__init__(f"invalid capability level for {family}: {level} (expected 0–100)")
