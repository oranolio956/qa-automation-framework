import math

from automation.core.timing_engine import TimingEngine, TimingContext, next_delay


def test_typing_delay_within_bounds():
    eng = TimingEngine()
    ctx = TimingContext(task="typing", base_seconds=0.2)
    for _ in range(100):
        d = eng.next_delay_seconds(ctx)
        assert 0.05 <= d <= 0.6


def test_entropy_changes_value():
    eng = TimingEngine()
    ctx_low = TimingContext(task="tap", base_seconds=0.3, entropy=0.01)
    ctx_high = TimingContext(task="tap", base_seconds=0.3, entropy=0.8)
    values_low = [eng.next_delay_seconds(ctx_low) for _ in range(20)]
    values_high = [eng.next_delay_seconds(ctx_high) for _ in range(20)]
    # High entropy should show wider spread than low entropy
    spread_low = max(values_low) - min(values_low)
    spread_high = max(values_high) - min(values_high)
    assert spread_high > spread_low


def test_fatigue_increases_delay():
    eng = TimingEngine()
    ctx_low = TimingContext(task="navigation", base_seconds=0.8, session_interactions=0)
    ctx_high = TimingContext(task="navigation", base_seconds=0.8, session_interactions=200)
    vals_low = [eng.next_delay_seconds(ctx_low) for _ in range(10)]
    vals_high = [eng.next_delay_seconds(ctx_high) for _ in range(10)]
    assert sum(vals_high) / len(vals_high) >= sum(vals_low) / len(vals_low)


def test_function_wrapper():
    d = next_delay(task="load", base_seconds=1.5)
    assert isinstance(d, float) and d > 0


