# ruff: noqa: E501


from .constants import ALL_MODELS


class FoundationModelFns:
    @staticmethod
    def get_foundation_model(name):
        try:
            return next(model for model in ALL_MODELS if model.model_name == name)
        except StopIteration:
            return None
