from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DesignTokens:
    background: str = "#030711"
    surface: str = "#07111F"
    surface_elevated: str = "#0B1728"
    border: str = "#18304A"
    text_primary: str = "#F4F8FF"
    text_secondary: str = "#91A4B8"
    active: str = "#00E5FF"
    info: str = "#278BFF"
    agent: str = "#8B5CF6"
    success: str = "#18D68C"
    warning: str = "#FFB020"
    danger: str = "#FF455D"
    evidence: str = "#FFC857"
    font_ui: str = "IBM Plex Sans Thai"
    font_heading: str = "Anuphan"
    font_mono: str = "JetBrains Mono"
    pulse_min_seconds: float = 1.8
    pulse_max_seconds: float = 2.4

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        color_values = (
            self.background,
            self.surface,
            self.surface_elevated,
            self.border,
            self.text_primary,
            self.text_secondary,
            self.active,
            self.info,
            self.agent,
            self.success,
            self.warning,
            self.danger,
            self.evidence,
        )
        for value in color_values:
            if len(value) != 7 or not value.startswith("#"):
                failures.append(f"invalid_color:{value}")
                continue
            try:
                int(value[1:], 16)
            except ValueError:
                failures.append(f"invalid_color:{value}")
        if not 0 < self.pulse_min_seconds <= self.pulse_max_seconds:
            failures.append("invalid_pulse_range")
        return tuple(failures)


DEFAULT_DESIGN_TOKENS = DesignTokens()
