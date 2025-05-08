from typing import Any

from dhenara.ai.types.genai.dhenara.request.data import ObjectTemplate


def is_string_hier_or_expr(v: str):
    return isinstance(v, str) and v.startswith(("$expr{", "$hier{"))


def ensure_object_template(v: str):
    if isinstance(v, ObjectTemplate):
        return v
    if is_string_hier_or_expr(v):
        return ObjectTemplate(expression=v)
    raise ValueError(
        f"ensure_object_template: {v} must be a instance of ObjectTemplate or string start with '$expr{{' or '$hier{{'"
    )


def auto_converr_str_to_template(v: Any) -> Any | ObjectTemplate:
    if is_string_hier_or_expr(v):
        return ObjectTemplate(expression=v)
    return v
