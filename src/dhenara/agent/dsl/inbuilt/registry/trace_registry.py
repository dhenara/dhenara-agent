# Global registry instance


from dhenara.agent.dsl.inbuilt.flow_nodes.ai_model import ai_model_node_tracing_profile
from dhenara.agent.observability.tracing.profile.profile import TracingProfileRegistry

tracing_profile_registry = TracingProfileRegistry()
tracing_profile_registry.register(ai_model_node_tracing_profile)
