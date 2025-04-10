# This can be added to one of your dashboard visualization modules


def link_related_runs(trace_data):
    """Find related runs (reruns, etc.) and create links between them."""
    # Group traces by agent ID
    agent_runs = {}
    for trace in trace_data:
        # Extract agent ID from trace
        root_id = trace.get("root_id")
        if not root_id:
            continue

        if root_id not in agent_runs:
            agent_runs[root_id] = []

        agent_runs[root_id].append(trace)

    # Find reruns by looking for previous_run_id attribute
    for _agent_id, traces in agent_runs.items():  # noqa: PERF102
        for trace in traces:
            if "previous_run_id" in trace:
                # This is a rerun, link it to its parent
                parent_id = trace["previous_run_id"]
                trace["parent_run"] = parent_id

                # Find the parent trace
                for potential_parent in traces:
                    if potential_parent.get("run_id") == parent_id:
                        # Create a bidirectional link
                        if "child_runs" not in potential_parent:
                            potential_parent["child_runs"] = []
                        potential_parent["child_runs"].append(trace["run_id"])
                        break

    return agent_runs
