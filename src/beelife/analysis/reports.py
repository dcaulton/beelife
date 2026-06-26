import json
from datetime import date, timedelta
from functools import partial

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.data_models import DateRange
from beelife.analysis.llm import LLMClient, Tool
from beelife.analysis.report_models import AnalysisReport
from beelife.analysis.tools import (
    get_activity_weather_correlation,
    get_daily_bee_activity,
    get_daily_weather_data,
)
from beelife.db.repositories import get_default_device

logger = structlog.get_logger(__name__)


async def generate_analysis_report(
    session: AsyncSession,
    device_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AnalysisReport:
    """
    Generate a structured weather + bee status analysis report using LLM + tools.
    """
    # --- Resolve device and date range ---
    if device_id is None:
        default_device = await get_default_device(session)
        if default_device is None:
            raise ValueError("No default device available. Please specify device_id.")
        device_id = default_device.device_id

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    logger.debug(
        "analysis_report_requested",
        device_id=device_id,
        start_date=str(start_date),
        end_date=str(end_date),
    )

    # --- Set up LLM and register tools ---
    llm = LLMClient(model="qwen2.5:32b")

    llm.register_tool(
        Tool(
            name="get_daily_weather_data",
            description="Get daily weather aggregates for a date range.",
            function=partial(get_daily_weather_data, session),
            parameters_model=DateRange,
        )
    )

    llm.register_tool(
        Tool(
            name="get_daily_bee_activity",
            description="Get daily bee activity (radar + vibration) aggregates.",
            function=partial(get_daily_bee_activity, session),
            parameters_model=DateRange,
        )
    )

    llm.register_tool(
        Tool(
            name="get_activity_weather_correlation",
            description="Analyze correlation between bee activity and weather.",
            function=partial(get_activity_weather_correlation, session),
            parameters_model=DateRange,
        )
    )

    # Temporarily disabled until we create proper input models
    # llm.register_tool(Tool(name="get_trend_comparison", ...))
    # llm.register_tool(Tool(name="get_weather_forecast", ...))

    # --- System prompt with structured output instruction ---
    system_prompt = f"""You are an expert beekeeping data analyst.

You have access to tools that can retrieve weather and bee activity data for device {device_id}.

Your task:
1. Use the available tools to gather relevant data between {start_date} and {end_date}.
2. Analyze weather trends, bee activity levels, and how weather affects the bees.
3. Return ONLY a valid JSON object that matches this exact schema:

{json.dumps(AnalysisReport.model_json_schema(), indent=2)}

Do not include any extra text before or after the JSON. Be concise but insightful.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Analyze the data for device {device_id} from {start_date} to {end_date} "
            f"and return the analysis as JSON.",
        },
    ]

    # --- Call LLM with tools ---
    final_message = await llm.call_with_tools(messages)

    # --- Parse final response into AnalysisReport ---
    try:
        content = final_message.get("content", "").strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        report = AnalysisReport.model_validate_json(content)
        logger.debug("analysis_report_parsed_successfully", device_id=device_id)
        return report

    except Exception as e:
        logger.exception("failed_to_parse_llm_response", error=str(e), raw_content=final_message.get("content"))
        raise ValueError("LLM failed to return valid structured output") from e
