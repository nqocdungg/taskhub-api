from pydantic import BaseModel, EmailStr, Field, field_validator


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if value is None:
            raise ValueError("email không được để trống")
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("full_name không được để trống")
        stripped = value.strip()
        if not stripped:
            raise ValueError("full_name không được để trống")
        return stripped


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)
