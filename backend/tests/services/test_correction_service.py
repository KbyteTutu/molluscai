import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.correction import CorrectionCreate
from app.services.correction_service import (
    create_correction,
    get_correction,
    get_correction_for_update,
    list_all_corrections,
    list_user_corrections,
)
from tests.conftest import MockResult, make_test_user


@pytest.mark.anyio
async def test_create_correction(mock_db, test_user):
    payload = CorrectionCreate(
        target_type="taxon",
        target_id="123",
        target_title="Conus textile",
        field_name="scientific_name",
        current_value="Conus textille",
        suggested_value="Conus textile",
        note="Fix typo",
    )

    correction = await create_correction(
        mock_db,
        test_user.id,
        payload,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert correction.user_id == test_user.id
    assert correction.target_type == payload.target_type
    assert correction.target_id == payload.target_id
    assert correction.field_name == payload.field_name
    assert correction.suggested_value == payload.suggested_value
    assert correction.ip_address == "127.0.0.1"
    assert correction.user_agent == "pytest"
    mock_db.add.assert_called_once_with(correction)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(correction)


@pytest.mark.anyio
async def test_list_user_corrections(mock_db, test_user):
    correction_one = type("CorrectionStub", (), {"id": 1, "created_at": datetime.now(timezone.utc)})()
    correction_two = type("CorrectionStub", (), {"id": 2, "created_at": datetime.now(timezone.utc)})()
    mock_db.execute.side_effect = [
        MockResult(scalar_val=2),
        MockResult(rows=[correction_one, correction_two]),
    ]

    rows, total = await list_user_corrections(mock_db, test_user.id, limit=10, offset=5)

    assert rows == [correction_one, correction_two]
    assert total == 2
    assert mock_db.execute.await_count == 2
    count_stmt = mock_db.execute.await_args_list[0].args[0]
    list_stmt = mock_db.execute.await_args_list[1].args[0]
    assert "count(corrections.id)" in str(count_stmt.compile())
    compiled_list = str(list_stmt.compile())
    assert "ORDER BY corrections.created_at DESC" in compiled_list
    assert " LIMIT " in compiled_list
    assert " OFFSET " in compiled_list


@pytest.mark.anyio
async def test_list_all_corrections(mock_db):
    correction = type(
        "CorrectionStub",
        (),
        {"id": 3, "status": "pending", "target_type": "taxon", "created_at": datetime.now(timezone.utc)},
    )()
    mock_db.execute.side_effect = [
        MockResult(scalar_val=1),
        MockResult(rows=[correction]),
    ]

    rows, total = await list_all_corrections(
        mock_db,
        status_filter="pending",
        target_type="taxon",
        limit=5,
        offset=0,
    )

    assert rows == [correction]
    assert total == 1
    assert mock_db.execute.await_count == 2
    count_stmt = mock_db.execute.await_args_list[0].args[0]
    list_stmt = mock_db.execute.await_args_list[1].args[0]
    compiled_count = str(count_stmt.compile())
    compiled_list = str(list_stmt.compile())
    assert "corrections.status =" in compiled_count
    assert "corrections.target_type =" in compiled_count
    assert "corrections.status =" in compiled_list
    assert "corrections.target_type =" in compiled_list


@pytest.mark.anyio
async def test_get_correction_found(mock_db):
    correction = type("CorrectionStub", (), {"id": 10})()
    mock_db.execute.return_value = MockResult(scalar_val=correction)

    result = await get_correction(mock_db, 10)

    assert result is correction


@pytest.mark.anyio
async def test_get_correction_not_found(mock_db):
    mock_db.execute.return_value = MockResult(scalar_val=None)

    result = await get_correction(mock_db, 404)

    assert result is None


@pytest.mark.anyio
async def test_get_correction_for_update(mock_db):
    correction = type("CorrectionStub", (), {"id": 11})()
    mock_db.execute.return_value = MockResult(scalar_val=correction)

    result = await get_correction_for_update(mock_db, 11)

    assert result is correction
    stmt = mock_db.execute.await_args.args[0]
    assert "FOR UPDATE" in str(stmt.compile())


@pytest.mark.anyio
async def test_make_test_user_helper_available_for_service_tests():
    user = make_test_user(user_id=uuid.uuid4(), username="corruser", email="corr@example.com")

    assert user.username == "corruser"
    assert user.email == "corr@example.com"
