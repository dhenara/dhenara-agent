from dhenara.agent.types.base import BaseModel


class NodeSettings(BaseModel):
    """Node Settings."""

    pass


class NodeOutcomeSettings(BaseModel):
    """Settings for recording node outcomes."""

    enabled: bool = True
    path_template: str = "{node_id}"
    filename_template: str = "{node_id}.json"
    content_template: str | None = None
    commit: bool = True
    commit_message_template: str | None = None
