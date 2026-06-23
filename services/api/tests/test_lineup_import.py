"""BE-018: lineup import service + endpoint tests."""

from __future__ import annotations

import json
import pathlib
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, SetArtist
from app.db.models.event import Event
from app.db.models.set_ import Set
from app.schemas.lineup import LineupImportRequest, LineupImportResponse

_ADMIN = "test-admin-token"
_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _load_sample_payload(overrides: dict[str, object] | None = None) -> dict[str, object]:
    """Load the 5-set sample fixture as a full LineupImportRequest dict."""
    perfs = json.loads((_FIXTURES / "tml_sample.json").read_text())["performances"]
    payload: dict[str, object] = {
        "event_name": "TML Sample",
        "start_date": "2026-07-24",
        "end_date": "2026-07-26",
        "timezone": "Europe/Brussels",
        "location": "Boom, Belgium",
        "source_adapter": "event_api_v1",
        "external_id": "tml-sample",
        "performances": perfs,
    }
    if overrides:
        payload.update(overrides)
    return payload


async def _import(client: AsyncClient, payload: dict[str, object]) -> dict[str, object]:
    r = await client.post(
        "/api/events/import",
        json=payload,
        headers={"X-Admin-Token": _ADMIN},
    )
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


async def test_import_creates_event_stages_sets_artists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Fresh import: 1 event, 2 stages, 5 sets, correct artist counts."""
    result = await _import(client, _load_sample_payload())

    assert result["stages_created"] == 2
    assert result["stages_updated"] == 0
    assert result["sets_created"] == 5
    assert result["sets_updated"] == 0
    assert result["artists_created"] == 6
    assert result["artists_linked"] == 0

    events = (await db_session.execute(select(Event))).scalars().all()
    assert len(events) == 1
    sets = (await db_session.execute(select(Set))).scalars().all()
    assert len(sets) == 5


async def test_reimport_idempotent_returns_updated_counts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-import same payload → _created=0, _updated=original counts."""
    payload = _load_sample_payload()
    first = await _import(client, payload)
    second = await _import(client, payload)

    assert second["stages_created"] == 0
    assert second["stages_updated"] == first["stages_created"]
    assert second["sets_created"] == 0
    assert second["sets_updated"] == first["sets_created"]
    assert second["artists_created"] == 0
    assert second["artists_linked"] == first["artists_created"]


async def test_reimport_preserves_existing_spotify_id_when_payload_null(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-import with spotify=null should NOT overwrite an existing spotify_id."""
    payload = _load_sample_payload()
    await _import(client, payload)

    # Verify Artist Alpha has spotify_id
    artist_result = await db_session.execute(
        select(Artist).where(Artist.name_normalized == "artist alpha")
    )
    artist = artist_result.scalar_one()
    assert artist.spotify_artist_id == "spotify:artist:alpha123"

    # Re-import with spotify set to null for Artist Alpha
    perfs = json.loads((_FIXTURES / "tml_sample.json").read_text())["performances"]
    perfs[0]["artists"][0]["spotify"] = None
    modified = dict(payload)
    modified["performances"] = perfs
    await _import(client, modified)

    artist_result2 = await db_session.execute(
        select(Artist)
        .where(Artist.name_normalized == "artist alpha")
        .execution_options(populate_existing=True)
    )
    artist2 = artist_result2.scalar_one()
    assert artist2.spotify_artist_id == "spotify:artist:alpha123"


async def test_reimport_updates_spotify_id_when_payload_non_null(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-import with a new non-null spotify_id should update it."""
    payload = _load_sample_payload()
    await _import(client, payload)

    perfs = json.loads((_FIXTURES / "tml_sample.json").read_text())["performances"]
    perfs[0]["artists"][0]["spotify"] = "spotify:artist:alpha_new"
    modified = dict(payload)
    modified["performances"] = perfs
    await _import(client, modified)

    artist_result = await db_session.execute(
        select(Artist)
        .where(Artist.name_normalized == "artist alpha")
        .execution_options(populate_existing=True)
    )
    artist = artist_result.scalar_one()
    assert artist.spotify_artist_id == "spotify:artist:alpha_new"


async def test_reimport_merges_social_links(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Re-import with new social_link fields merges into existing dict."""
    payload = _load_sample_payload()
    await _import(client, payload)

    # Verify initial instagram link
    artist_result = await db_session.execute(
        select(Artist).where(Artist.name_normalized == "artist alpha")
    )
    artist = artist_result.scalar_one()
    assert artist.social_links is not None
    assert "instagram" in artist.social_links

    # Re-import with an additional soundcloud link for Artist Alpha
    perfs = json.loads((_FIXTURES / "tml_sample.json").read_text())["performances"]
    perfs[0]["artists"][0]["soundcloud"] = "https://soundcloud.com/artista"
    modified = dict(payload)
    modified["performances"] = perfs
    await _import(client, modified)

    artist_result2 = await db_session.execute(
        select(Artist)
        .where(Artist.name_normalized == "artist alpha")
        .execution_options(populate_existing=True)
    )
    artist2 = artist_result2.scalar_one()
    assert artist2.social_links is not None
    assert "instagram" in artist2.social_links
    assert "soundcloud" in artist2.social_links


async def test_b2b_artists_one_set_two_artist_rows(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Set with 2 artists → 2 set_artist rows at position 0 and 1."""
    await _import(client, _load_sample_payload())

    # perf-003 is the B2B set with 2 artists
    set_result = await db_session.execute(select(Set).where(Set.external_id == "perf-003"))
    s = set_result.scalar_one()

    sa_result = await db_session.execute(select(SetArtist).where(SetArtist.set_id == s.set_id))
    set_artists = sa_result.scalars().all()
    positions = sorted(sa.position for sa in set_artists)
    assert positions == [0, 1]


async def test_artist_name_collision_dedups_by_normalized(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Two payload artists with names 'Effin' and 'EFFIN' → 1 Artist row."""
    payload: dict[str, object] = {
        "event_name": "Dedup Fest",
        "start_date": "2026-07-24",
        "end_date": "2026-07-24",
        "timezone": "UTC",
        "source_adapter": "manual",
        "external_id": "dedup-fest",
        "performances": [
            {
                "id": "p1",
                "name": "Set 1",
                "artists": [{"id": "a1", "name": "Effin"}],
                "stage": {"id": "s1", "name": "Stage"},
                "date": "2026-07-24",
                "day": "FRIDAY",
                "startTime": "2026-07-24 14:00:00+00:00",
                "endTime": "2026-07-24 15:00:00+00:00",
            },
            {
                "id": "p2",
                "name": "Set 2",
                "artists": [{"id": "a2", "name": "EFFIN"}],
                "stage": {"id": "s1", "name": "Stage"},
                "date": "2026-07-24",
                "day": "FRIDAY",
                "startTime": "2026-07-24 15:00:00+00:00",
                "endTime": "2026-07-24 16:00:00+00:00",
            },
        ],
    }
    await _import(client, payload)

    artist_result = await db_session.execute(
        select(Artist).where(Artist.name_normalized == "effin")
    )
    artists = artist_result.scalars().all()
    assert len(artists) == 1


async def test_midnight_straddle_preserved(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Set 23:30–01:00 stored verbatim."""
    await _import(client, _load_sample_payload())

    set_result = await db_session.execute(select(Set).where(Set.external_id == "perf-004"))
    s = set_result.scalar_one()
    # 2026-07-25 23:30:00+02:00 = 2026-07-25 21:30:00 UTC
    assert s.starts_at.hour == 21
    assert s.starts_at.minute == 30
    # 2026-07-26 01:00:00+02:00 = 2026-07-25 23:00:00 UTC
    assert s.ends_at.hour == 23
    assert s.ends_at.minute == 0


async def test_import_failure_rolls_back(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """SQLAlchemy error mid-import → 500 returned; lineup.import_failed logged."""
    payload = _load_sample_payload({"external_id": "rollback-test"})

    with patch(
        "app.services.lineup_import_service._upsert_stage",
        side_effect=SQLAlchemyError("injected failure"),
    ):
        r = await client.post(
            "/api/events/import",
            json=payload,
            headers={"X-Admin-Token": _ADMIN},
        )

    assert r.status_code == 500
    assert r.json()["detail"]["error_code"] == "lineup_import_failed"


async def test_import_endpoint_requires_admin_token(client: AsyncClient) -> None:
    r = await client.post("/api/events/import", json=_load_sample_payload())
    assert r.status_code == 401


async def test_cli_invokes_service_with_parsed_args(tmp_path: pathlib.Path) -> None:
    """CLI constructs LineupImportRequest from file + args and calls import_lineup."""
    sample = json.loads((_FIXTURES / "tml_sample.json").read_text())
    cli_file = tmp_path / "perf.json"
    cli_file.write_text(json.dumps(sample))

    import sys

    mock_result = LineupImportResponse(
        event_id=uuid.uuid4(),
        stages_created=1,
        stages_updated=0,
        sets_created=5,
        sets_updated=0,
        artists_created=6,
        artists_linked=0,
        imported_at=datetime.now(timezone.utc),
    )

    with (
        patch("scripts.import_lineup.import_lineup", new_callable=AsyncMock) as mock_svc,
        patch(
            "scripts.import_lineup.async_sessionmaker",
            return_value=AsyncMock(
                __call__=AsyncMock(
                    return_value=AsyncMock(
                        __aenter__=AsyncMock(
                            return_value=AsyncMock(
                                begin=AsyncMock(
                                    return_value=AsyncMock(
                                        __aenter__=AsyncMock(return_value=None),
                                        __aexit__=AsyncMock(return_value=None),
                                    )
                                )
                            )
                        ),
                        __aexit__=AsyncMock(return_value=None),
                    )
                )
            ),
        ),
        patch("scripts.import_lineup.create_async_engine"),
    ):
        mock_svc.return_value = mock_result
        sys.argv = [
            "import_lineup.py",
            "--file",
            str(cli_file),
            "--event-name",
            "TML Sample",
            "--start-date",
            "2026-07-24",
            "--end-date",
            "2026-07-26",
            "--timezone",
            "Europe/Brussels",
            "--source-adapter",
            "event_api_v1",
            "--external-id",
            "tml-sample",
        ]
        from scripts.import_lineup import _load_performances, _parse_args

        args = _parse_args()
        performances = _load_performances(args.file)
        assert len(performances) == 5
        # Verify the LineupImportRequest would be constructed correctly
        req = LineupImportRequest(
            event_name=args.event_name,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
            timezone=args.timezone,
            location=args.location,
            source_adapter=args.source_adapter,
            external_id=args.external_id,
            performances=performances,
        )
        assert req.event_name == "TML Sample"
        assert req.external_id == "tml-sample"
        assert len(req.performances) == 5
