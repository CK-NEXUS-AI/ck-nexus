from creator_app.core.deterministic_state import DeterministicState


def test_same_seed_and_input_produce_same_digest() -> None:
    first = DeterministicState(seed=42)
    second = DeterministicState(seed=42)

    assert first.digest({"b": 2, "a": 1}) == second.digest({"a": 1, "b": 2})


def test_choice_is_stable_for_same_seed_key_and_options() -> None:
    first = DeterministicState(seed=42)
    second = DeterministicState(seed=42)
    options = ["a", "b", "c", "d"]

    assert first.choice(key="task:1", options=options) == second.choice(
        key="task:1",
        options=options,
    )


def test_choice_does_not_depend_on_call_order() -> None:
    state = DeterministicState(seed=42)
    options = [1, 2, 3, 4, 5]

    first = state.choice(key="stable", options=options)
    state.choice(key="other", options=options)
    second = state.choice(key="stable", options=options)

    assert first == second
