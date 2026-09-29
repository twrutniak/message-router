from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints

from app.settings import settings

Message = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=settings.message_max_length),
]


class RouteRequest(BaseModel):
    email: EmailStr = Field(description="Adres e-mail nadawcy (trafi do nagłówka Reply-To).")
    message: Message = Field(description="Treść wiadomości do skierowania do właściwego działu.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "jan.nowak@example.com", "message": "Chciałbym zgłosić urlop na jutro"}
            ]
        }
    }


class RouteResponse(BaseModel):
    status: Literal["sent", "fallback"] = Field(
        description="`sent` – agent wysłał wiadomość; `fallback` – wysłano do działu domyślnego."
    )
    routed_to: str = Field(description="Adres działu, do którego wysłano wiadomość.")
    subject: str = Field(description="Temat wysłanego e-maila.")
