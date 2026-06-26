import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import ollama
import structlog
from pydantic import BaseModel

from beelife.core.config import settings

logger = structlog.get_logger(__name__)


class Tool:
    """Wrapper for a tool the LLM can call."""

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable[..., Awaitable[Any]],
        parameters_model: type[BaseModel],
    ) -> None:
        self.name = name
        self.description = description
        self.function = function
        self.parameters_model = parameters_model

    def to_ollama_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_model.model_json_schema(),
            },
        }


class LLMClient:
    def __init__(self, model: str | None = None, client: ollama.Client | None = None) -> None:
        self.model = model or settings.ollama_model
        self.client = client or ollama.Client(host=settings.ollama_base_url)
        self.tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    async def call_with_tools(
        self,
        messages: list[dict],
        max_tool_rounds: int = 3,
    ) -> dict[str, Any]:
        """
        Call the LLM and handle tool execution (supports parallel tool calls).
        """
        tool_schemas = [t.to_ollama_schema() for t in self.tools.values()]

        for round_num in range(max_tool_rounds):
            logger.debug(
                "llm_call_start",
                round=round_num + 1,
                model=self.model,
            )

            response = self.client.chat(
                model=self.model,
                messages=messages,
                tools=tool_schemas,
            )

            message = response["message"]
            messages.append(message)

            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                logger.debug("llm_final_answer", content=message.get("content"))
                return messages[-1]

            # Execute all tool calls in parallel
            tasks = []
            for tool_call in tool_calls:
                function = tool_call["function"]
                tool_name = function["name"]
                arguments = function.get("arguments", {})

                if tool_name not in self.tools:
                    logger.warning("unknown_tool_called", tool=tool_name)
                    continue

                tool = self.tools[tool_name]
                validated_args = tool.parameters_model(**arguments)

                logger.debug(
                    "tool_call",
                    tool=tool_name,
                    arguments=arguments,
                )

                # Schedule the tool execution
                tasks.append(self._execute_tool(tool, validated_args))

            if tasks:
                tool_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in tool_results:
                    if isinstance(result, Exception):
                        logger.exception("tool_execution_failed", error=str(result))
                        messages.append(
                            {
                                "role": "tool",
                                "content": f"Error: {result}",
                            }
                        )
                    else:
                        messages.append(
                            {
                                "role": "tool",
                                "content": str(result),
                            }
                        )

        logger.warning("max_tool_rounds_exceeded", max_rounds=max_tool_rounds)
        return messages[-1]

    async def _execute_tool(self, tool: Tool, validated_args: BaseModel) -> Any:
        """Execute a single tool and return its result."""
        return await tool.function(**validated_args.model_dump())
