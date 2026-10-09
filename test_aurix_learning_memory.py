import numpy as np

from aurix_learning import (
    LinUCBBandit,
    context_vector,
    eligible_actions,
    extract_signals,
    feedback_reward,
)

from aurix_world_memory import (
    EpisodicMemory,
    scene_novelty,
)


# ===============================================================
# RESONANCE SIGNALS
# ===============================================================

def test_direct_question_cannot_choose_silence():

    signals = extract_signals(
        "why is my code failing?"
    )

    allowed = eligible_actions(
        signals
    )

    assert "silence" not in allowed


def test_low_information_can_allow_silence():

    signals = extract_signals(
        "ugh"
    )

    allowed = eligible_actions(
        signals
    )

    assert "silence" in allowed


def test_context_vector_has_expected_size():

    vector, signals = context_vector(
        "explain transformers in detail"
    )

    assert vector.shape == (
        11,
    )

    assert signals[
        "detail_request"
    ] is True


def test_feedback_reward():

    assert feedback_reward(
        "feedback good"
    ) == 1.0

    assert feedback_reward(
        "feedback bad"
    ) == -1.0


# ===============================================================
# BANDIT LEARNING
# ===============================================================

def test_bandit_learns_positive_reward(
    tmp_path
):

    path = (
        tmp_path
        / "bandit.json"
    )

    bandit = LinUCBBandit(
        path=str(
            path
        ),
        alpha=0.0,
    )

    x = np.ones(
        bandit.dimension
    )

    before = bandit.score(
        "brief_direct",
        x,
    )

    for _ in range(
        5
    ):

        bandit.update(
            "brief_direct",
            x,
            1.0,
        )

    after = bandit.score(
        "brief_direct",
        x,
    )

    assert after > before


def test_bandit_persists(
    tmp_path
):

    path = (
        tmp_path
        / "bandit.json"
    )

    first = LinUCBBandit(
        path=str(
            path
        ),
        alpha=0.0,
    )

    x = np.ones(
        first.dimension
    )

    first.update(
        "normal",
        x,
        1.0,
    )

    second = LinUCBBandit(
        path=str(
            path
        ),
        alpha=0.0,
    )

    assert (
        second.score(
            "normal",
            x,
        )
        > 0
    )


# ===============================================================
# EPISODIC MEMORY
# ===============================================================

def test_episode_persists(
    tmp_path
):

    db = (
        tmp_path
        / "world.db"
    )

    memory = EpisodicMemory(
        str(
            db
        )
    )

    memory.add_episode(
        modality="conversation",
        event_type="test",
        summary="AURIX test event",
    )

    assert memory.count() == 1

    latest = memory.latest()

    assert (
        latest["summary"]
        == "AURIX test event"
    )


def test_search_memory(
    tmp_path
):

    db = (
        tmp_path
        / "world.db"
    )

    memory = EpisodicMemory(
        str(
            db
        )
    )

    memory.add_episode(
        modality="user",
        event_type="explicit_memory",
        summary="charger is near the monitor",
    )

    results = memory.search(
        "charger"
    )

    assert len(
        results
    ) == 1


# ===============================================================
# WORLD CHANGE
# ===============================================================

def test_identical_scene_has_low_novelty():

    scene = (
        "A laptop and keyboard are on the desk."
    )

    assert scene_novelty(
        scene,
        scene,
    ) == 0.0


def test_different_scene_has_higher_novelty():

    old = (
        "A laptop keyboard and cup are on the desk."
    )

    new = (
        "A bicycle and cardboard package are near a doorway."
    )

    assert scene_novelty(
        old,
        new,
    ) > 0.5


def test_vision_change_is_recorded(
    tmp_path
):

    db = (
        tmp_path
        / "world.db"
    )

    memory = EpisodicMemory(
        str(
            db
        )
    )

    first = (
        memory.record_vision_observation(
            "Laptop keyboard monitor desk."
        )
    )

    second = (
        memory.record_vision_observation(
            "Bicycle package doorway floor."
        )
    )

    assert first[
        "changed"
    ] is False

    assert second[
        "changed"
    ] is True

    change = memory.latest(
        event_type="scene_change"
    )

    assert change is not None