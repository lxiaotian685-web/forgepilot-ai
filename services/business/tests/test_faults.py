from __future__ import annotations


def auth(
    ids: dict, org: str = "demo-org", user: str = "demo@example.com"
) -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_device_fault_history_links_chain(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-07/faults", headers=auth(ids)
    )
    assert response.status_code == 200
    item = next(
        entry
        for entry in response.json()["items"]
        if entry["alertId"] == "ALT-0941"
    )
    assert item["deviceId"] == "AC-07"
    assert item["diagnosisId"] == "DIAG-20250518-0941"
    assert item["workOrderId"] == "WO-20250518-01"
    assert item["status"] == "待确认"
    assert item["maintenanceRecordId"] is None


def test_fault_history_includes_maintenance_record(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-08/faults", headers=auth(ids)
    )
    assert response.status_code == 200
    item = next(
        entry
        for entry in response.json()["items"]
        if entry["alertId"] == "ALT-0911"
    )
    assert item["workOrderId"] == "WO-20250516-04"
    assert item["maintenanceRecordId"] is not None
    assert item["resolvedAt"] is not None


def test_fault_history_cross_org_404(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-07/faults",
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert response.status_code == 404


def test_fault_history_filter_by_status(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-07/faults",
        params={"status": "待确认"},
        headers=auth(ids),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["status"] == "待确认" for item in items)
