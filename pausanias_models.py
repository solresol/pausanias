"""Current defaults for the standalone Pausanias Chat Completions scripts."""

TEXT_MODEL = "gpt-6.1-sol"
ANNOTATION_MODEL = "gpt-6-luna"
SPLIT_FALLBACK_MODEL = "gpt-6-sol"


def tool_call_options(model: str) -> dict[str, str]:
    """Use the required no-reasoning mode for these Chat Completions tools."""
    if model in (ANNOTATION_MODEL, SPLIT_FALLBACK_MODEL):
        return {"reasoning_effort": "none"}
    return {}
