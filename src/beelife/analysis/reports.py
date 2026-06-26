import json
from datetime import UTC, date, datetime, timedelta
from functools import partial
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from beelife.analysis.data_models import DateRange, WeatherForecastInput
from beelife.analysis.llm import LLMClient, Tool
from beelife.analysis.report_models import AnalysisReport
from beelife.analysis.tools import (
    get_activity_weather_correlation,
    get_daily_bee_activity,
    get_daily_weather_data,
    get_weather_forecast,
)
from beelife.db.models import AnalysisReportRecord
from beelife.db.repositories import get_default_device

logger = structlog.get_logger(__name__)


async def generate_analysis_report(
    session: AsyncSession,
    device_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    report_id: UUID | None = None,
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
        "analysis_report_start",
        device_id=device_id,
        start_date=str(start_date),
        end_date=str(end_date),
        report_id=str(report_id) if report_id else None,
    )

    # --- Set up LLM and register tools ---
    llm = LLMClient()

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

    llm.register_tool(
        Tool(
            name="get_weather_forecast",
            description=(
                "Get the 7-day weather forecast from the National Weather Service "
                "for the device's location. You should call this tool to populate "
                "the forecast_7day_summary field in the final report."
            ),
            function=partial(get_weather_forecast, session),
            parameters_model=WeatherForecastInput,
        )
    )

    # Temporarily disabled until we create proper input models
    # llm.register_tool(Tool(name="get_trend_comparison", ...))

    # --- System prompt with structured output instruction ---
    system_prompt = f"""You are an expert beekeeping data analyst.

    You have access to tools that can retrieve:
    - Historical and current weather data
    - Bee activity data (radar + vibration)
    - Correlations between weather and bee behavior
    - Weather forecasts from the National Weather Service

    Your task is to analyze the period from {start_date} to {end_date} for device {device_id}.

    **Critical instructions:**
    - You **must** call the `get_weather_forecast` tool to get the 7-day outlook.
    - Use the forecast data to include a meaningful `forecast_7day_summary` in your final report.
    - After using tools, return ONLY a valid JSON object matching the `AnalysisReport` schema below.
    - Do not include any text, explanations, or markdown before or after the JSON.

    After using tools, you must output ONLY the final JSON report. Do not output any more
    function calls or tool JSON objects.

    Schema:
    {json.dumps(AnalysisReport.model_json_schema(), indent=2)}
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Analyze the data for device {device_id} from {start_date} to {end_date} "
            f"and return only the JSON analysis report.",
        },
    ]

    # --- Call LLM with tools + force JSON output ---
    final_message = await llm.call_with_tools(messages)

    # After getting final_message from llm.call_with_tools()

    try:
        content = final_message.get("content", "").strip()

        # Clean markdown if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.lower().startswith("json"):
                content = content[4:].strip()

        # Guard: detect if the model returned another tool call instead of the report
        if content.strip().startswith("{") and '"name":' in content and '"arguments":' in content:
            logger.error(
                "llm_returned_tool_call_instead_of_report",
                raw_content=content,
            )
            raise ValueError("Model returned a tool call instead of the final structured report")

        report = AnalysisReport.model_validate_json(content)

    except Exception as e:
        logger.error(
            "llm_structured_output_failed",
            raw_content=final_message.get("content"),
            error_type=type(e).__name__,
            error=str(e),
        )
        raise ValueError(f"LLM failed to return valid structured output: {e}") from e

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    # Only reach here if parsing succeeded
    if report_id:
        record = await session.get(AnalysisReportRecord, report_id)
        if record:
            record.status = "completed"
            record.completed_at = datetime.now(UTC)
            record.period_start = start_date
            record.period_end = end_date
            record.report_data = report.model_dump(mode="json")
            await session.commit()

    return report
