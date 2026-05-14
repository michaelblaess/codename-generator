from __future__ import annotations

import random

from codename_generator.phonetic import mutate


def test_mutate_returns_different_word_for_long_input() -> None:
    word = "Pegasus"
    seen = {mutate(word, random.Random(seed)) for seed in range(20)}
    seen.discard(word)
    assert len(seen) >= 3, f"Expected at least 3 distinct mutations, got {seen}"


def test_mutate_preserves_word_when_intensity_zero() -> None:
    rng = random.Random(0)
    assert mutate("Zeus", rng, intensity=0) == "Zeus"


def test_mutate_short_word_handles_gracefully() -> None:
    rng = random.Random(0)
    result = mutate("Ra", rng)
    assert isinstance(result, str)
    assert len(result) >= 1
