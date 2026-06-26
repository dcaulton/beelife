from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from beelife.analysis.llm import LLMClient, Tool


class DummyInput(BaseModel):
    value: str


async def dummy_tool(value: str) -> dict[str, str]:
    return {"result": f"processed {value}"}


@pytest.mark.asyncio
async def test_llm_client_tool_calling() -> None:
    # First response = tool call, second response = final answer
    mock_responses = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "dummy_tool",
                            "arguments": {"value": "hello"},
                        }
                    }
                ],
            }
        },
        {
            "message": {
                "role": "assistant",
                "content": "Task completed successfully.",
                "tool_calls": [],
            }
        },
    ]

    mock_client = MagicMock()
    mock_client.chat.side_effect = mock_responses

    llm = LLMClient(model="test-model", client=mock_client)

    tool = Tool(
        name="dummy_tool",
        description="A test tool",
        function=dummy_tool,
        parameters_model=DummyInput,
    )
    llm.register_tool(tool)

    result = await llm.call_with_tools([{"role": "user", "content": "do something"}])

    assert result["role"] == "assistant"
    assert "completed" in result.get("content", "").lower()
    assert mock_client.chat.call_count == 2
