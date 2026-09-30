from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, model_validator

from app.settings import settings


class DepartmentsConfigError(ValueError):
    """Niepoprawny plik z działami – API nie może wystartować."""


class Department(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    address: EmailStr
    description: str = Field(min_length=1)
    keywords: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()


class DepartmentsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fallback: EmailStr
    departments: tuple[Department, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_addresses(self) -> Self:
        addresses = [d.address for d in self.departments]
        duplicates = sorted({a for a in addresses if addresses.count(a) > 1})
        if duplicates:
            raise ValueError(f"adresy działów muszą być unikalne, powtórzone: {duplicates}")
        if self.fallback not in addresses:
            raise ValueError(f"fallback {self.fallback} nie występuje na liście działów")
        return self


def load_departments(path: Path) -> DepartmentsConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return DepartmentsConfig.model_validate(raw)
    except OSError as exc:
        raise DepartmentsConfigError(f"Nie można odczytać pliku z działami {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise DepartmentsConfigError(f"Niepoprawny YAML w pliku {path}: {exc}") from exc
    except ValidationError as exc:
        raise DepartmentsConfigError(f"Niepoprawna konfiguracja działów w {path}:\n{exc}") from exc


_config = load_departments(settings.departments_file)

DEPARTMENTS: tuple[Department, ...] = _config.departments
FALLBACK_ADDRESS: str = _config.fallback
ALLOWED_ADDRESSES: tuple[str, ...] = tuple(d.address for d in DEPARTMENTS)
