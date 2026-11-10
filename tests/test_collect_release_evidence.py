from __future__ import annotations

import pytest

from scripts import collect_release_evidence as collector


def test_source_tree_is_resolved_from_github_commit_object(monkeypatch):
    source_sha = "a" * 40
    source_tree = "b" * 40
    calls = []

    def fake_run_json(command):
        calls.append(command)
        return {"sha": source_sha, "tree": {"sha": source_tree}}

    monkeypatch.setattr(collector, "run_json", fake_run_json)
    assert collector.resolve_source_tree("CK-NEXUS-AI/ck-nexus", source_sha) == source_tree
    assert calls == [
        [
            "gh",
            "api",
            "repos/CK-NEXUS-AI/ck-nexus/git/commits/" + source_sha,
        ]
    ]


@pytest.mark.parametrize(
    "commit",
    [
        {"sha": "c" * 40, "tree": {"sha": "b" * 40}},
        {"sha": "a" * 40, "tree": {"sha": "not-a-tree-sha"}},
        {"sha": "a" * 40, "tree": {}},
    ],
)
def test_source_tree_rejects_unbound_or_invalid_github_commit_objects(monkeypatch, commit):
    monkeypatch.setattr(collector, "run_json", lambda _command: commit)
    with pytest.raises(SystemExit):
        collector.resolve_source_tree("CK-NEXUS-AI/ck-nexus", "a" * 40)
