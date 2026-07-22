from dataclasses import dataclass


@dataclass(slots=True)
class PublicError(Exception):
    status_code: int
    code: str
    message: str
