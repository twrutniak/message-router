from dataclasses import dataclass


@dataclass(frozen=True)
class Department:
    address: str
    description: str
    keywords: tuple[str, ...]


DEPARTMENTS: tuple[Department, ...] = (
    Department(
        address="kadry@example.com",
        description=(
            "Sprawy pracownicze i administracyjne: urlopy, zwolnienia lekarskie, umowy o pracę, "
            "wynagrodzenia, premie, listy płac, świadectwa pracy, wypowiedzenia."
        ),
        keywords=(
            "urlop",
            "umowa",
            "wypłata",
            "pensja",
            "zwolnienie",
            "L4",
            "wypowiedzenie",
            "premia",
        ),
    ),
    Department(
        address="human-resources@example.com",
        description=(
            "Ludzie i kultura organizacji: rekrutacja i onboarding, rozwój i szkolenia, "
            "ścieżki kariery, benefity, ocena pracownicza, atmosfera w zespole, konflikty."
        ),
        keywords=(
            "rekrutacja",
            "praca",
            "CV",
            "szkolenie",
            "rozwój",
            "benefity",
            "onboarding",
            "awans",
        ),
    ),
    Department(
        address="it@example.com",
        description=(
            "Sprzęt i infrastruktura: awarie komputerów i laptopów, oprogramowanie, licencje, "
            "dostępy i uprawnienia do systemów, konta, VPN, sieć, drukarki, bezpieczeństwo."
        ),
        keywords=("komputer", "laptop", "nie działa", "hasło", "dostęp", "VPN", "sieć", "drukarka"),
    ),
    Department(
        address="help-desk@example.com",
        description=(
            "Pierwsza linia wsparcia: ogólne pytania typu „jak coś zrobić” oraz sprawy biurowe "
            "niepasujące do IT ani działów kadrowych, np. zamówienie materiałów, rezerwacja sali."
        ),
        keywords=("jak", "gdzie", "pomoc", "instrukcja", "pytanie", "biuro", "rezerwacja"),
    ),
    Department(
        address="other@example.com",
        description=(
            "Fallback: wiadomości niezrozumiałe, bez związku z pracą lub niepasujące do żadnego "
            "z pozostałych działów."
        ),
        keywords=(),
    ),
)

FALLBACK_ADDRESS = "other@example.com"

ALLOWED_ADDRESSES: tuple[str, ...] = tuple(d.address for d in DEPARTMENTS)
