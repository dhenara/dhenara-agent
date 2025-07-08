from ..profile import TracingAttribute

# Define TracingAttribute instances for method tracing
fn_class_attr = TracingAttribute(
    name="class_name",
    category="secondary",
    group_name="fn_trace",
    data_type="string",
    display_name="Class",
    description="Name of the class containing the method",
)

fn_method_attr = TracingAttribute(
    name="method_name",
    category="secondary",
    group_name="fn_trace",
    data_type="string",
    display_name="Method",
    description="Name of the method being traced",
)

fn_code_namespace_attr = TracingAttribute(
    name="namespace",
    category="tertiary",
    group_name="fn_trace",
    data_type="string",
    display_name="Code Namespace",
    description="Module namespace of the method",
)

fn_execution_time_attr = TracingAttribute(
    name="time_ms",
    category="primary",
    group_name="fn_trace",
    data_type="number",
    display_name="Execution Time (ms)",
    description="Method execution time in milliseconds",
    format_hint="duration",
)

fn_error_type_attr = TracingAttribute(
    name="type",
    category="primary",
    group_name="fn_trace",
    data_type="string",
    display_name="Error Type",
    description="Type of error that occurred",
)

fn_error_message_attr = TracingAttribute(
    name="message",
    category="primary",
    group_name="fn_trace",
    data_type="string",
    display_name="Error Message",
    description="Error message details",
    max_length=1000,
)


fn_result_type_attr = TracingAttribute(
    name="fn_result_type",
    category="secondary",
    group_name="fn_trace",
    data_type="string",
    display_name="Result Type",
    description="Type of the returned result",
)

fn_result_size_attr = TracingAttribute(
    name="fn_result_size",
    category="secondary",
    group_name="fn_trace",
    data_type="number",
    display_name="Result Size",
    description="Size of the result (for collections)",
)

fn_result_keys_attr = TracingAttribute(
    name="fn_result_keys",
    category="tertiary",
    group_name="fn_trace",
    data_type="array",
    display_name="Result Keys",
    description="Keys of the result (for dictionaries)",
    max_length=500,
)

fn_result_status_attr = TracingAttribute(
    name="fn_result_status",
    category="secondary",
    group_name="fn_trace",
    data_type="string",
    display_name="Result Status",
    description="Status field from the result object",
)

fn_result_status_code_attr = TracingAttribute(
    name="fn_result_status_code",
    category="secondary",
    group_name="fn_trace",
    data_type="number",
    display_name="Result Status Code",
    description="HTTP status code from the result",
)

fn_result_success_attr = TracingAttribute(
    name="fn_result_success",
    category="primary",
    group_name="fn_trace",
    data_type="boolean",
    display_name="Result Success",
    description="Success flag from the result object",
)

common_fn_trace_attributes: list[TracingAttribute] = [
    fn_class_attr,
    fn_method_attr,
    fn_code_namespace_attr,
    fn_execution_time_attr,
    fn_error_type_attr,
    fn_error_message_attr,
    fn_result_type_attr,
    fn_result_size_attr,
    fn_result_keys_attr,
    fn_result_status_attr,
    fn_result_status_code_attr,
    fn_result_success_attr,
]
