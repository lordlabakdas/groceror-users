from typing import Literal, Optional
from pydantic import BaseModel

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}


class UserRegisteredEvent(BaseModel):
    schema_version: str = "1.0"
    event: Literal["user_registered"]
    user_id: str
    phone: str
    entity_type: str


class OTPVerifiedEvent(BaseModel):
    schema_version: str = "1.0"
    event: Literal["otp_verified"]
    user_id: str
    phone: str


class ProfileUpdatedEvent(BaseModel):
    schema_version: str = "1.0"
    event: Literal["profile_updated"]
    user_id: str
    profile_id: str
    entity_type: str
    name: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None


class PasswordChangedEvent(BaseModel):
    schema_version: str = "1.0"
    event: Literal["password_changed"]
    user_id: str
    phone: str


EVENT_MODELS = {
    "user_registered": UserRegisteredEvent,
    "otp_verified": OTPVerifiedEvent,
    "profile_updated": ProfileUpdatedEvent,
    "password_changed": PasswordChangedEvent,
}


def parse_event(data: dict):
    """Validate an event dict and return a typed model instance.

    Raises:
        ValueError: unknown schema_version or event type
        pydantic.ValidationError: payload does not match the model
    """
    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported schema_version: {version!r}")

    event_type = data.get("event")
    model_cls = EVENT_MODELS.get(event_type)
    if model_cls is None:
        raise ValueError(f"Unknown event type: {event_type!r}")

    return model_cls(**data)
