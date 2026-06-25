# beelife

**BeeDar + Weather data ingestion, analysis, and hive health summaries.**

Part of the Weathervane multi-modal beekeeping intelligence ecosystem.

This service ingests data from your BroodMinder BeeDar (radar activity + vibration) and weather data exported from MyBroodMinder. It provides structured data access, trend analysis (including LLM-assisted summaries), and formatted charts.

## Goals

- Clean, consistent architecture with `sound-detection` (good portfolio piece)
- Local-first with TimescaleDB for time-series data
- Easy correlation between BeeDar readings and weather
- Foundation for future LLM-powered insights

## Local Development Setup

### 1. Initial Setup

```bash
make install
cp .env.example .env
make pre-commit-install  # for dev only
```

### 2. Start Local Database (TimescaleDB)

```bash
make docker-up
```

This starts a TimescaleDB container on **port 5434** (to avoid conflicts with your other projects).

### 3. Update your `.env` file

Make sure your `DATABASE_URL` points to port **5434**:

```env
DATABASE_URL=postgresql+psycopg://beelife:beelife_dev@localhost:5434/beelife
```

### 4. Enable TimescaleDB Extension (one-time)

Connect to the database and run:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

You only need to do this once per database.

### 5. Run Migrations

```bash
make migrate
```

This will create tables and convert time-series tables (`beedar_readings`, `weather_observations`, etc.) into **hypertables**.

### 6. Run the Application

```bash
make run
```

The app will be available at `http://localhost:8000` (or the port defined in your config).

---

## Working with TimescaleDB

### Creating Hypertables

In your Alembic migrations (or manually), convert tables like this:

```sql
SELECT create_hypertable('beedar_readings', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
```

### Recommended Practices

- Use `timestamp` (timestamptz) as the partitioning column.
- Enable compression on older chunks for better performance.
- Use continuous aggregates for common rollups (daily averages, etc.).

We will add helper functions/migrations for this as the models are created.

---

## Common Commands

| Command              | Description                              |
|----------------------|------------------------------------------|
| `make install`       | Install dependencies with uv             |
| `make docker-up`     | Start local TimescaleDB (port 5434)      |
| `make docker-down`   | Stop the database container              |
| `make migrate`       | Run Alembic migrations                   |
| `make run`           | Start the FastAPI app                    |
| `make test`          | Run tests (uses testcontainers)          |
| `make lint`          | Run ruff + mypy                          |
| `make format`        | Format code with ruff                    |

---

## Architecture Notes

- Follows the same structure and conventions as `sound-detection`
- Uses `SQLModel` + async SQLAlchemy
- Time-series tables are stored as TimescaleDB hypertables
- Weather and BeeDar data live together in this service for now (can be exposed later via the Weathervane supervisor)
- Designed to support both raw data access and LLM-assisted analysis

---

## Production Considerations

- PostGIS and TimescaleDB can run together in the same database.
- New time-series tables should be created as hypertables from the start.
- Existing PostGIS tables do not need to be converted unless you want time-series features on them.

---

## Next Steps

We are currently building:
- Database models for BeeDar readings and weather observations
- CSV upload endpoints
- Basic query + summary endpoints
