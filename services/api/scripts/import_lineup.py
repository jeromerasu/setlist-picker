"""CLI wrapper for lineup import.

Usage:
    uv run python scripts/import_lineup.py \\
      --file .local-data/tml26-w2.json \\
      --event-name "Tomorrowland 2026 W2" \\
      --start-date 2026-07-24 \\
      --end-date 2026-07-26 \\
      --timezone Europe/Brussels \\
      --location "Boom, Belgium" \\
      --source-adapter event_api_v1 \\
      --external-id tml-2026-w2

The JSON file must contain either:
  - A dict with a "performances" key  (recommended)
  - A top-level JSON array of performances
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.schemas.lineup import LineupImportRequest, LineupSourcePerformance
from app.services.lineup_import_service import import_lineup


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a festival lineup into the database.")
    parser.add_argument("--file", required=True, help="Path to lineup JSON file.")
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--timezone", required=True, help="IANA timezone, e.g. Europe/Brussels")
    parser.add_argument("--location", default=None)
    parser.add_argument(
        "--source-adapter",
        required=True,
        choices=["event_api_v1", "manual"],
    )
    parser.add_argument("--external-id", default=None)
    return parser.parse_args()


def _load_performances(path: str) -> list[LineupSourcePerformance]:
    with open(path) as f:
        raw = json.load(f)
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and "performances" in raw:
        items = raw["performances"]
    else:
        print(
            f"ERROR: {path} must be a JSON array or a dict with a 'performances' key",
            file=sys.stderr,
        )
        sys.exit(1)
    return [LineupSourcePerformance.model_validate(item) for item in items]


async def _run(args: argparse.Namespace) -> None:
    performances = _load_performances(args.file)
    payload = LineupImportRequest(
        event_name=args.event_name,
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
        timezone=args.timezone,
        location=args.location,
        source_adapter=args.source_adapter,
        external_id=args.external_id,
        performances=performances,
    )

    settings = Settings()
    engine = create_async_engine(str(settings.database_url), echo=False)
    session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    async with session_maker() as db:
        async with db.begin():
            result = await import_lineup(db, payload)

    await engine.dispose()

    print(f"event_id:        {result.event_id}")
    print(f"stages_created:  {result.stages_created}")
    print(f"stages_updated:  {result.stages_updated}")
    print(f"sets_created:    {result.sets_created}")
    print(f"sets_updated:    {result.sets_updated}")
    print(f"artists_created: {result.artists_created}")
    print(f"artists_linked:  {result.artists_linked}")


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_run(args))
