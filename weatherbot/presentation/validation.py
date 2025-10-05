"""Pydantic-powered validation helpers for user-facing inputs."""

from __future__ import annotations

from typing import Any, Type, TypeVar

try:  # pragma: no cover - runtime dependency resolution
    from pydantic import (
        BaseModel,
    )
    from pydantic import ValidationError as PydanticValidationError  # type: ignore
    from pydantic import (
        field_validator,
    )
except ImportError:  # pragma: no cover - fallback for restricted environments

    class PydanticValidationError(Exception):
        """Lightweight stand-in mirroring Pydantic's validation error."""

        def __init__(self, errors: list[str]) -> None:
            super().__init__("; ".join(errors))
            self._errors = [{"msg": message} for message in errors]

        def errors(self) -> list[dict[str, str]]:
            return list(self._errors)

    def field_validator(field_name: str):  # type: ignore[misc]
        def decorator(func):
            target = getattr(func, "__func__", func)
            setattr(target, "__field_name__", field_name)
            setattr(func, "__field_name__", field_name)
            return func

        return decorator

    class _BaseModelMeta(type):
        def __new__(mcls, name, bases, namespace):
            validators: dict[str, Any] = {}
            for base in bases:
                validators.update(getattr(base, "_validators", {}))
            for attr_name, value in namespace.items():
                field_name = getattr(value, "__field_name__", None)
                validator = value
                if field_name is None and hasattr(value, "__func__"):
                    func = value.__func__  # type: ignore[attr-defined]
                    field_name = getattr(func, "__field_name__", None)
                    validator = value
                if field_name:
                    validators[field_name] = validator
            namespace["_validators"] = validators
            return super().__new__(mcls, name, bases, namespace)

    class BaseModel(metaclass=_BaseModelMeta):  # type: ignore[misc]
        """Minimal subset of :class:`pydantic.BaseModel` used for validation."""

        @classmethod
        def model_validate(cls, data: dict[str, Any]):
            errors: list[str] = []
            values: dict[str, Any] = {}
            annotations = getattr(cls, "__annotations__", {})
            for field, _type in annotations.items():
                raw_value = data.get(field)
                validator = cls._validators.get(field)  # type: ignore[attr-defined]
                try:
                    if validator:
                        bound_validator = (
                            validator.__get__(None, cls)
                            if hasattr(validator, "__get__")
                            else validator
                        )
                        raw_value = bound_validator(raw_value)
                except Exception as exc:  # pragma: no cover - fallback path
                    errors.append(str(exc))
                values[field] = raw_value
            if errors:
                raise PydanticValidationError(errors)
            instance = cls.__new__(cls)
            for field, value in values.items():
                setattr(instance, field, value)
            return instance


from weatherbot.core.exceptions import ValidationError


class CityInputModel(BaseModel):
    """Normalize and validate city names provided by users."""

    city: str

    @field_validator("city")
    @classmethod
    def _normalize_city(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("City name must be a string")
        value = value.strip()
        if not value:
            raise ValueError("City name cannot be empty")
        return value


class SubscribeTimeModel(BaseModel):
    """Validate raw time input for subscription commands."""

    time: str

    @field_validator("time")
    @classmethod
    def _normalize_time(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Time value must be a string")
        value = value.strip()
        if not value:
            raise ValueError("Time value cannot be empty")
        if len(value) > 10:
            raise ValueError("Time value is unexpectedly long")
        return value


ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_payload(model: Type[ModelT], **data: Any) -> ModelT:
    """Validate ``data`` against ``model`` and raise domain errors on failure."""

    try:
        return model.model_validate(data)
    except PydanticValidationError as err:  # pragma: no cover - exercised indirectly
        message = "; ".join(detail["msg"] for detail in err.errors())
        raise ValidationError(message) from err


__all__ = ["CityInputModel", "SubscribeTimeModel", "validate_payload"]
