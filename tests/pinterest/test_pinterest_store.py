from creator_app.global_knowledge.pinterest_store import PinterestReferenceStore


def test_store_upserts_references_without_copying_image_bytes(tmp_path):
    store = PinterestReferenceStore(tmp_path / "pins.sqlite3")
    row = {
        "pin_id": "123",
        "board_id": "456",
        "title": "AI agent architecture",
        "image_url": "https://i.pinimg.com/1200x/abc.jpg",
        "rights_status": "unknown",
        "reusable": False,
    }
    assert store.upsert([row]) == 1
    assert store.upsert([row]) == 1
    assert store.summary() == {"pin_reference_count": 1, "board_count": 1}
    assert store.list(limit=10) == [row]
    raw = (tmp_path / "pins.sqlite3").read_bytes()
    assert b"image bytes" not in raw


def test_store_deduplicates_same_pin_across_boards(tmp_path):
    store = PinterestReferenceStore(tmp_path / "pins.sqlite3")
    first = {"pin_id": "123", "board_id": "456", "title": "First"}
    duplicate = {"pin_id": "123", "board_id": "789", "title": "Updated"}
    assert store.upsert([first, duplicate]) == 1
    assert store.summary() == {"pin_reference_count": 1, "board_count": 1}
    assert store.list(limit=10)[0]["title"] == "Updated"
