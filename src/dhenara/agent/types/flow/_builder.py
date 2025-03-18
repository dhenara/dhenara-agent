from dhenara.agent.types.flow import (
    BaseFlowDefinition,
    ConditionalFlow,
    ExecutionStrategyEnum,
    FlowDefinition,
    FlowNode,
    LoopFlow,
    ResponseProtocolEnum,
    SwitchFlow,
)


# dhenara/agent/types/flow/_builder.py
class FlowBuilder:
    """Helper class for building flow definitions."""

    @staticmethod
    def create_standard_flow(
        nodes: list[FlowNode],
        execution_strategy: ExecutionStrategyEnum = ExecutionStrategyEnum.sequential,
        response_protocol: ResponseProtocolEnum = ResponseProtocolEnum.HTTP,
        system_instructions: list[str] | None = None,
    ) -> FlowDefinition:
        """Create a standard flow with nodes."""
        return FlowDefinition(
            nodes=nodes,
            execution_strategy=execution_strategy,
            response_protocol=response_protocol,
            system_instructions=system_instructions,
        )

    @staticmethod
    def create_conditional_flow(
        condition_expr: str,
        true_branch: BaseFlowDefinition,
        false_branch: BaseFlowDefinition | None = None,
        response_protocol: ResponseProtocolEnum = ResponseProtocolEnum.HTTP,
        system_instructions: list[str] | None = None,
        context_vars: list[str] | None = None,
    ) -> ConditionalFlow:
        """Create a conditional flow."""
        return ConditionalFlow(
            condition_expr=condition_expr,
            true_branch=true_branch,
            false_branch=false_branch,
            response_protocol=response_protocol,
            system_instructions=system_instructions,
            context_vars=context_vars or [],
        )

    @staticmethod
    def create_for_loop_flow(
        items_expr: str,
        body: BaseFlowDefinition,
        max_iterations: int | None = 100,
        item_var: str = "item",
        iteration_var: str = "iteration",
        capture_results: bool = True,
        pass_state: bool = True,
        response_protocol: ResponseProtocolEnum = ResponseProtocolEnum.HTTP,
        system_instructions: list[str] | None = None,
        context_vars: list[str] | None = None,
    ) -> LoopFlow:
        """Create a for loop flow."""
        return LoopFlow(
            loop_type="for",
            items_expr=items_expr,
            body=body,
            max_iterations=max_iterations,
            item_var=item_var,
            iteration_var=iteration_var,
            capture_results=capture_results,
            pass_state=pass_state,
            response_protocol=response_protocol,
            system_instructions=system_instructions,
            context_vars=context_vars or [],
        )

    @staticmethod
    def create_while_loop_flow(
        condition_expr: str,
        body: BaseFlowDefinition,
        max_iterations: int | None = 100,
        iteration_var: str = "iteration",
        capture_results: bool = True,
        pass_state: bool = True,
        response_protocol: ResponseProtocolEnum = ResponseProtocolEnum.HTTP,
        system_instructions: list[str] | None = None,
        context_vars: list[str] | None = None,
    ) -> LoopFlow:
        """Create a while loop flow."""
        return LoopFlow(
            loop_type="while",
            condition_expr=condition_expr,
            body=body,
            max_iterations=max_iterations,
            iteration_var=iteration_var,
            capture_results=capture_results,
            pass_state=pass_state,
            response_protocol=response_protocol,
            system_instructions=system_instructions,
            context_vars=context_vars or [],
        )

    @staticmethod
    def create_switch_flow(
        switch_expr: str,
        cases: dict[str, BaseFlowDefinition],
        default: BaseFlowDefinition | None = None,
        response_protocol: ResponseProtocolEnum = ResponseProtocolEnum.HTTP,
        system_instructions: list[str] | None = None,
        context_vars: list[str] | None = None,
    ) -> SwitchFlow:
        """Create a switch flow."""
        return SwitchFlow(
            switch_expr=switch_expr,
            cases=cases,
            default=default,
            response_protocol=response_protocol,
            system_instructions=system_instructions,
            context_vars=context_vars or [],
        )
