from typing import Annotated
from pydantic import Field

# E.164: + followed by 7–15 digits, first digit non-zero (e.g. +14165551234)
E164Phone = Annotated[str, Field(pattern=r"^\+[1-9]\d{6,14}$")]
