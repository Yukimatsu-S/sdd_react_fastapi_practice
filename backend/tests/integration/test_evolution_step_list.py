"""Specify keyset paging against a migration-created MySQL Evolution Step table."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.engine import Connection

from app.infrastructure.evolution_step_repository import EvolutionStepRepository

CREATED_AT = datetime(2026, 9, 18, 10, 0, tzinfo=UTC).replace(tzinfo=None)


def test_list_uses_created_at_then_id_descending_without_boundary_duplicates(
    migrated_schema: Callable[[], AbstractContextManager[Connection]],
) -> None:
    """Keep the pre-insertion continuation stable while a fresh list sees the new row."""
    with migrated_schema() as connection:
        repository = EvolutionStepRepository(connection)
        for number in range(1, 22):
            repository.create(
                purpose=f"purpose {number}",
                hypothesis="hypothesis",
                change_description=None,
                parent_run_id=None,
                result_run_id=None,
                now=CREATED_AT,
            )
        connection.commit()

        first_page = repository.list_page(page_token=None)
        inserted = repository.create(
            purpose="newest after first page",
            hypothesis="hypothesis",
            change_description=None,
            parent_run_id=None,
            result_run_id=None,
            now=CREATED_AT,
        )
        connection.commit()
        second_page = repository.list_page(page_token=first_page.next_page_token)
        fresh_page = repository.list_page(page_token=None)

    assert [item.id for item in first_page.items] == list(range(21, 1, -1))
    assert [item.id for item in second_page.items] == [1]
    assert {item.id for item in first_page.items}.isdisjoint(item.id for item in second_page.items)
    assert fresh_page.items[0].id == inserted.id
