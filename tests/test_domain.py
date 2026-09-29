from app.domain_keywords import ALLOWED_ADDRESSES, DEPARTMENTS, FALLBACK_ADDRESS
from app.prompts import build_system_prompt


def test_required_addresses_present():
    assert set(ALLOWED_ADDRESSES) == {
        "human-resources@example.com",
        "help-desk@example.com",
        "it@example.com",
        "kadry@example.com",
        "other@example.com",
    }


def test_addresses_unique_and_fallback_allowed():
    assert len(set(ALLOWED_ADDRESSES)) == len(ALLOWED_ADDRESSES)
    assert FALLBACK_ADDRESS in ALLOWED_ADDRESSES


def test_system_prompt_lists_every_department():
    prompt = build_system_prompt()
    for department in DEPARTMENTS:
        assert department.address in prompt
        assert department.description in prompt
        for keyword in department.keywords:
            assert keyword in prompt
    assert prompt == prompt.strip()
