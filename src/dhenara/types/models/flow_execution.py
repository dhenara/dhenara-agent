
from pydantic import Field, field_validator

from ..base import BaseModel


class FlowExecution(BaseModel):
    input: str = Field(..., max_length=1000, description="User input for the AI model.")
    # Add other fields as necessary

    @field_validator("input")
    @classmethod
    def sanitize_input(cls, v: str) -> str:
        ## Example sanitization: remove script tags
        # sanitized = re.sub(r"<script.*?>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)

        sanitized = v
        if len(sanitized) > 1000:
            raise ValueError("Input exceeds maximum allowed length.")
        return sanitized
