import pytest


@pytest.mark.anyio
async def test_functionx_health(client):
    response = await client.get("/api/functionx/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "functionx"


@pytest.mark.anyio
async def test_create_and_get_action_set(client):
    create_response = await client.post(
        "/api/functionx/sets",
        json={
            "name": "Set Alpha",
            "actions": ["upload_documents", "run_analysis"],
            "metadata": {"source": "manual"},
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_response.status_code == 200

    created = create_response.json()
    set_id = created["set_id"]
    assert created["status"] == "planned"
    assert created["actions_count"] == 2

    get_response = await client.get(f"/api/functionx/sets/{set_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["set_id"] == set_id
    assert fetched["name"] == "Set Alpha"


@pytest.mark.anyio
async def test_execute_action_set_dry_run_and_real(client):
    create_response = await client.post(
        "/api/functionx/sets",
        json={
            "name": "Set Beta",
            "actions": ["step_1", "step_2", "step_3"],
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    set_id = create_response.json()["set_id"]

    dry_run_response = await client.post(
        f"/api/functionx/sets/{set_id}/execute",
        json={"dry_run": True},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert dry_run_response.status_code == 200
    dry_payload = dry_run_response.json()
    assert dry_payload["dry_run"] is True
    assert dry_payload["status"] == "planned"

    execute_response = await client.post(
        f"/api/functionx/sets/{set_id}/execute",
        json={"dry_run": False},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert execute_response.status_code == 200
    exec_payload = execute_response.json()
    assert exec_payload["dry_run"] is False
    assert exec_payload["status"] == "executed"
    assert exec_payload["processed_actions"] == 3


@pytest.mark.anyio
async def test_missing_action_set_returns_404(client):
    get_response = await client.get("/api/functionx/sets/fx_missing")
    assert get_response.status_code == 404

    execute_response = await client.post(
        "/api/functionx/sets/fx_missing/execute",
        json={"dry_run": False},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert execute_response.status_code == 404


@pytest.mark.anyio
async def test_create_action_set_denied_for_user_role(client):
    response = await client.post(
        "/api/functionx/sets",
        json={
            "name": "Denied Set",
            "actions": ["a1"],
        },
        cookies={"semptify_uid": "GUtest1234"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_create_and_execute_allowed_for_advocate_role(client):
    create_response = await client.post(
        "/api/functionx/sets",
        json={
            "name": "Allowed Set",
            "actions": ["a1", "a2"],
        },
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert create_response.status_code == 200
    set_id = create_response.json()["set_id"]

    execute_response = await client.post(
        f"/api/functionx/sets/{set_id}/execute",
        json={"dry_run": False},
        cookies={"semptify_uid": "GVtest1234"},
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "executed"
