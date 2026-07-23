from pydantic import BaseModel, ConfigDict, model_validator


class AIOutputModel(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_explicit_null_defaults(cls, value):
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        for name, field in cls.model_fields.items():
            if name not in normalized or normalized[name] is not None:
                continue
            if field.default_factory is not None:
                normalized[name] = field.default_factory()
            elif not field.is_required():
                normalized[name] = field.default
        return normalized
