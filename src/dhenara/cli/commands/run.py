import asyncio
import importlib
import logging
import os
from datetime import datetime

import click
from dhenara.agent.engine import FlowOrchestrator
from dhenara.agent.types.flow import Flow, FlowContext, FlowDefinition, FlowNodeInput, UserInput
from dhenara.ai.types import ResourceConfig
from dhenara.ai.types.shared.platform import DhenaraAPIError
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

# Set logger level for a specific package
logging.getLogger("dhenara.agent").setLevel(logging.DEBUG)


def register(cli):
    cli.add_command(run)


@click.group(name="run")
def run():
    """Create new Dhenara components."""
    pass


@run.command("flow")
@click.option("--path", prompt="Flow definition path", help="Eg: src.agents.<my_agent>.flows.<my_flow>")
@click.option("--flow_name", default="flow", help="Name of FlowDefinition within the file")
@click.option("--initial_input_name", default="initial_input", help="Name of UserInput within the file")
def run_flow(path, flow_name, initial_input_name):
    """Run a flow."""
    try:
        # Add current directory to path
        import sys

        sys.path.append(os.getcwd())

        # Import flow from path
        module_path = path
        module = importlib.import_module(module_path)
        flow = getattr(module, flow_name)
        initial_input = getattr(module, initial_input_name)

        if not isinstance(flow, Flow):
            logger.error(f"Imported object is not a Flow: {type(flow)}")
            return

        if not isinstance(initial_input, FlowNodeInput):
            logger.error(f"Imported input is not a FlowNodeInput: {type(initial_input)}")
            return

        # Run the async function in an event loop
        asyncio.run(
            _run_flow(
                flow_definition=flow.definition,
                initial_input=initial_input,
            )
        )
    except ImportError as e:
        logger.error(f"Failed to import flow from path {path}: {e}")
    except AttributeError as e:
        logger.error(f"Failed to find flow definition in module {path}: {e}")


async def _run_flow(flow_definition: FlowDefinition, initial_input):
    try:
        node_input = initial_input

        resource_config = load_resource_config()

        flow_orchestrator = FlowOrchestrator(
            flow_definition=flow_definition,
            resource_config=resource_config,
        )

        flow_context = FlowContext(
            flow_definition=flow_definition,
            initial_input=node_input,
            created_at=datetime.now(),
        )

        # Execute
        await flow_orchestrator.execute(flow_context)

        # Set `is_streaming` after execution returns
        is_streaming = flow_orchestrator.flow_definition.has_any_streaming_node()

        if flow_context.execution_failed:
            logger.exception(f"Execution Failed: {flow_context.execution_failed_message}")
            return False

        if is_streaming:
            response_stream_generator = flow_context.stream_generator
            print(f"Steam generator is: {response_stream_generator}")
        else:
            response_data = {
                "execution_status": flow_context.execution_status,
                "execution_results": flow_context.execution_results,
            }
            print(f"response_data: {response_data}")

    except PydanticValidationError as e:
        raise DhenaraAPIError(f"Invalid Inputs {e}")

    logger.debug("process_post: run completed")


def load_resource_config():
    resource_config = ResourceConfig()
    resource_config.load_from_file(
        credentials_file="~/.env_keys/.dhenara_credentials.yaml",
    )
    print(f"resource_config={resource_config}")  # TODO
    return resource_config


def _validate_node_input(user_input: UserInput) -> FlowNodeInput:
    try:
        return FlowNodeInput.model_validate(user_input)
    except PydanticValidationError as e:
        raise DhenaraAPIError(f"Invalid input format: {e!s}")
