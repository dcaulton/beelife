import base64
import io
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from beelife.analysis.report_models import AnalysisReport
from beelife.core.config import settings

SAVE_TO_DISK = settings.analysis_save_graph_files
GRAPH_DIR = Path("reports/graphs")
GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def _fig_to_base64(fig: Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _save_graph(fig: Figure, filename: str) -> None:
    """Save figure to disk using flat structure."""
    filepath = GRAPH_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filepath, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def generate_activity_vs_weather_graph(report: AnalysisReport, report_id: str) -> str | None:
    """Temperature + Radar Activity dual-axis chart."""
    # TODO: Replace placeholder data with real daily aggregated data
    import datetime

    dates = [report.weather_report.period_start + datetime.timedelta(days=i) for i in range(8)]
    temps = [68, 71, 65, 72, 74, 69, 73, 76]
    activity = [45, 52, 38, 61, 55, 48, 59, 63]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Temperature (°F)", color="tab:red")
    ax1.plot(dates, temps, color="tab:red", marker="o")  # type: ignore[arg-type]
    ax1.tick_params(axis="y", labelcolor="tab:red")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Radar Activity", color="tab:blue")
    ax2.plot(dates, activity, color="tab:blue", marker="s")  # type: ignore[arg-type]
    ax2.tick_params(axis="y", labelcolor="tab:blue")

    plt.title("Temperature vs Bee Activity")
    fig.autofmt_xdate()

    base64_str = _fig_to_base64(fig)

    if SAVE_TO_DISK:
        filename = f"{report_id}_activity_vs_weather.png"
        _save_graph(fig, filename)

    return base64_str


def generate_precipitation_activity_graph(report: AnalysisReport, report_id: str) -> str | None:
    """Precipitation + Bee Activity chart."""
    import datetime

    dates = [report.weather_report.period_start + datetime.timedelta(days=i) for i in range(8)]
    precip = [0.0, 0.2, 0.8, 0.1, 0.0, 0.3, 0.0, 0.0]
    activity = [52, 45, 28, 55, 60, 42, 58, 61]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(dates, precip, color="skyblue", alpha=0.6, label="Precipitation")  # type: ignore[arg-type]
    ax2 = ax.twinx()
    ax2.plot(dates, activity, color="darkgreen", marker="o", label="Radar Activity")  # type: ignore[arg-type]

    ax.set_ylabel("Precipitation (in)")
    ax2.set_ylabel("Radar Activity")
    plt.title("Precipitation Impact on Bee Activity")
    fig.autofmt_xdate()

    base64_str = _fig_to_base64(fig)

    if SAVE_TO_DISK:
        filename = f"{report_id}_precipitation_activity.png"
        _save_graph(fig, filename)

    return base64_str


def generate_report_graphs(report: AnalysisReport, report_id: str) -> dict[str, str | None]:
    """Generate both graphs and return base64 versions."""
    graphs = {}

    graphs["activity_vs_weather"] = generate_activity_vs_weather_graph(report, report_id)
    graphs["precipitation_activity"] = generate_precipitation_activity_graph(report, report_id)

    return graphs
