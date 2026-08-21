import errno
import os
from pathlib import Path

import pytest

from creator_app.core.durable_persistence import JsonlDurableStore
from creator_app.core.durable_runtime import Checkpoint


@pytest.mark.chaos
def test_disk_full_does_not_append_corrupt_jsonl(
    tmp_path: Path,
    ck_chaos_level: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if ck_chaos_level < 3:
        pytest.skip("requires --chaos-level=3")

    state_path = tmp_path / "state.jsonl"
    store = JsonlDurableStore(state_path)
    checkpoint = Checkpoint(
        checkpoint_id="cp:disk-full",
        subject="chaos",
        state_digest="sha256:safe",
    )

    def raise_enospc(fd: int, data: bytes) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(os, "write", raise_enospc)
    with pytest.raises(OSError, match="No space left on device"):
        store.append_checkpoint(checkpoint)

    if state_path.exists():
        assert state_path.read_bytes() == b""
