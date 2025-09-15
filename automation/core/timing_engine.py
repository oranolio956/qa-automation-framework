"""
Timing Engine: Generates human-like, non-deterministic delays for automation steps.

This module centralizes delay logic so flows do not use fixed sleeps. It supports
personality, circadian rhythm, fatigue accumulation, and task context.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class TimingContext:
    """Contextual signals that influence delays."""
    personality: str = "methodical"  # cautious|confident|impulsive|methodical
    session_interactions: int = 0     # increases fatigue over time
    task: str = "generic"            # typing|tap|navigation|load|verification
    base_seconds: float = 0.5         # baseline for the task, before modifiers
    entropy: float = 0.15             # randomization strength (0..1)


class TimingEngine:
    """Produce human-like delays with variance and anti-fingerprinting properties."""

    def __init__(self, circadian_strength: float = 0.6, fatigue_rate: float = 0.02):
        self.circadian_strength = max(0.0, min(1.0, circadian_strength))
        self.fatigue_rate = max(0.0, min(0.2, fatigue_rate))  # max 20% slower per 10 interactions

    def _task_baseline(self, task: str, base_seconds: float) -> float:
        # Task-specific baseline guidance
        presets = {
            "typing": (0.12, 0.28),   # per keystroke cadence
            "tap": (0.15, 0.45),      # simple interactions
            "navigation": (0.3, 1.0), # multi-step UI changes
            "load": (1.2, 3.0),       # network-bound waits
            "verification": (2.0, 5.0),
            "generic": (0.3, 1.2),
        }
        lo, hi = presets.get(task, presets["generic"])
        return max(lo, min(hi, base_seconds))

    def _personality_multiplier(self, personality: str) -> float:
        # Slower/faster depending on archetype
        lookup = {
            "cautious": (1.05, 1.25),
            "methodical": (0.95, 1.15),
            "confident": (0.9, 1.05),
            "impulsive": (0.75, 0.95),
        }
        lo, hi = lookup.get(personality, lookup["methodical"])
        return random.uniform(lo, hi)

    def _circadian_multiplier(self, now: Optional[datetime] = None) -> float:
        # Slowdowns at night and afternoon dip; mild speed at evening peak
        now = now or datetime.now()
        hour = now.hour + now.minute / 60.0
        # Use a smooth curve to avoid discrete fingerprints
        # Map to [-1,1] and then scale by circadian strength
        wave = math.sin((hour / 24.0) * 2 * math.pi)
        # Night penalty: shift wave to penalize early morning
        penalty = 1.0 + (-0.2 * wave) * self.circadian_strength
        return max(0.75, min(1.35, penalty))

    def _fatigue_multiplier(self, interactions: int) -> float:
        # 2% per 10 interactions by default, capped at +50%
        factor = 1.0 + (interactions / 10.0) * self.fatigue_rate
        return min(factor, 1.5)

    def _entropy_jitter(self, seconds: float, entropy: float) -> float:
        # Apply symmetric jitter proportional to entropy and duration
        jitter = (random.random() - 0.5) * 2.0 * entropy
        scale = 0.35 + 0.65 * min(1.0, seconds / 2.0)  # longer waits tolerate more jitter
        return seconds * (1.0 + jitter * scale)

    def next_delay_seconds(self, ctx: TimingContext) -> float:
        base = self._task_baseline(ctx.task, ctx.base_seconds)
        p = self._personality_multiplier(ctx.personality)
        c = self._circadian_multiplier()
        f = self._fatigue_multiplier(ctx.session_interactions)
        raw = base * p * c * f
        final = self._entropy_jitter(raw, ctx.entropy)
        # Bound the delay to sane limits per task
        bounds = {
            "typing": (0.05, 0.6),
            "tap": (0.05, 1.0),
            "navigation": (0.15, 3.0),
            "load": (0.5, 8.0),
            "verification": (1.0, 30.0),
            "generic": (0.05, 5.0),
        }
        lo, hi = bounds.get(ctx.task, bounds["generic"])
        return max(lo, min(hi, final))


# Convenience singleton with default parameters
default_engine = TimingEngine()


def next_delay(task: str = "generic", base_seconds: float = 0.5, personality: str = "methodical",
               session_interactions: int = 0, entropy: float = 0.15) -> float:
    """Functional wrapper for simple callsites."""
    ctx = TimingContext(
        personality=personality,
        session_interactions=session_interactions,
        task=task,
        base_seconds=base_seconds,
        entropy=entropy,
    )
    return default_engine.next_delay_seconds(ctx)


