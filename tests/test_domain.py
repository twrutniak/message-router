from pathlib import Path

import pytest

from app.domain_keywords import (
    ALLOWED_ADDRESSES,
    DEPARTMENTS,
    FALLBACK_ADDRESS,
    DepartmentsConfigError,
    load_departments,
)
from app.prompts import build_system_prompt
from app.settings import settings

VALID_YAML = """
fallback: other@example.com
departments:
  - address: it@example.com
    description: Sprzęt i sieć.
    keywords: [laptop, VPN]
    examples: [Nie działa laptop]
  - address: other@example.com
    description: Reszta.
"""


def write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "departments.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_shipped_config_is_valid():
    config = load_departments(settings.departments_file)

    assert tuple(d.address for d in config.departments) == ALLOWED_ADDRESSES
    assert config.fallback == FALLBACK_ADDRESS


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


def test_system_prompt_hides_examples():
    prompt = build_system_prompt()
    for department in DEPARTMENTS:
        for example in department.examples:
            assert example not in prompt


def test_load_valid_config(tmp_path):
    config = load_departments(write_yaml(tmp_path, VALID_YAML))

    it, other = config.departments
    assert (it.address, it.keywords, it.examples) == (
        "it@example.com",
        ("laptop", "VPN"),
        ("Nie działa laptop",),
    )
    assert other.keywords == () and other.examples == ()
    assert config.fallback == "other@example.com"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            VALID_YAML.replace("fallback: other@example.com", "fallback: nieznany@example.com"),
            "fallback",
        ),
        (VALID_YAML.replace("address: other@example.com", "address: it@example.com"), "unikalne"),
        (VALID_YAML.replace("address: it@example.com", "address: to-nie-email"), "address"),
        (VALID_YAML.replace("Sprzęt i sieć.", '""'), "description"),
        (VALID_YAML.replace("keywords:", "keyword:"), "keyword"),
        (VALID_YAML.replace("[laptop, VPN]", "[no, laptop]"), "keywords"),
        ("fallback: other@example.com\ndepartments: []", "departments"),
        ("departments: [\n", "YAML"),
        ("- to nie jest słownik", "Niepoprawna konfiguracja"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, content, expected):
    with pytest.raises(DepartmentsConfigError, match=expected):
        load_departments(write_yaml(tmp_path, content))


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(DepartmentsConfigError, match="Nie można odczytać"):
        load_departments(tmp_path / "brak.yaml")
