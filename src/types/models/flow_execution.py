import re
from pydantic import Field, field_validator

from ..base import BaseModel


class FlowExecutionModel(BaseModel):
    input: str = Field(..., max_length=1000, description="User input for the AI model.")
    # Add other fields as necessary

    @field_validator("input")
    def sanitize_input(cls, value):
        # Example sanitization: remove script tags
        sanitized = re.sub(r"<script.*?>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
        if len(sanitized) > 1000:
            raise ValueError("Input exceeds maximum allowed length.")
        return sanitized
