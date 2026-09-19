import pytest

from app.prompts.loader import load_prompt


def test_load_prompt_v1():
    content, content_hash = load_prompt("v1")
    assert len(content) > 0
    assert len(content_hash) == 64
    assert "v1 Baseline" in content


def test_load_prompt_v2():
    content, content_hash = load_prompt("v2")
    assert len(content) > 0
    assert len(content_hash) == 64
    assert "Anti-Prompt-Injection" in content
    assert "Few-Shot Reference Examples" in content


def test_prompt_hash_stability():
    c1, h1 = load_prompt("v2")
    c2, h2 = load_prompt("v2")
    assert c1 == c2
    assert h1 == h2


def test_load_nonexistent_prompt():
    with pytest.raises(FileNotFoundError) as exc:
        load_prompt("v999")
    assert "Không tìm thấy file prompt cho phiên bản: 'v999'" in str(exc.value)
