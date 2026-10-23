from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AuditLog,
    Device,
    DeviceComponent,
    DeviceParameter,
    Diagnosis,
    MaintenanceRecord,
    Membership,
    Organization,
    Plant,
    User,
    WorkOrder,
)
from app.security import hash_password

# 固定 UUID，便于演示环境与接口示例复现；数据全部为虚构。
ORG_DEMO_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
ORG_NORTH_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")

USER_OWNER_ID = uuid.UUID("00000000-0000-4000-8000-000000000101")
USER_TECH_ID = uuid.UUID("00000000-0000-4000-8000-000000000102")
USER_MANAGER_ID = uuid.UUID("00000000-0000-4000-8000-000000000103")
USER_VIEWER_ID = uuid.UUID("00000000-0000-4000-8000-000000000104")
USER_OTHER_ID = uuid.UUID("00000000-0000-4000-8000-000000000105")
USER_ZHAO_ID = uuid.UUID("00000000-0000-4000-8000-000000000106")

BASE = datetime(2026, 5, 18, 9, 44, tzinfo=timezone.utc)

DEMO_PASSWORD = "ForgePilot123!"
DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)

TREND_POINTS = [
    (0, 3.1, 67),
    (20, 3.2, 69),
    (40, 3.4, 72),
    (58, 4.8, 76),
    (72, 6.1, 81),
    (84, 7.82, 88.5),
    (102, 7.4, 91),
]


def _collect_ids(db: Session) -> dict:
    organizations = {
        org.code: org.id for org in db.scalars(select(Organization)).all()
    }
    users = {user.email: user.id for user in db.scalars(select(User)).all()}
    devices = {device.code: device.id for device in db.scalars(select(Device)).all()}
    return {
        "organizations": organizations,
        "users": users,
        "devices": devices,
    }


def seed_demo(db: Session) -> dict:
    existing = db.scalar(
        select(Organization).where(Organization.code == "demo-org")
    )
    if existing is not None:
        return _collect_ids(db)

    demo_org = Organization(
        id=ORG_DEMO_ID,
        code="demo-org",
        name="虚构演示制造企业",
    )
    north_org = Organization(
        id=ORG_NORTH_ID,
        code="northwind-org",
        name="虚构北方机械企业",
    )
    db.add_all([demo_org, north_org])
    db.flush()

    owner = User(
        id=USER_OWNER_ID,
        email="demo@example.com",
        display_name="李振华",
        password_hash=DEMO_PASSWORD_HASH,
    )
    tech = User(
        id=USER_TECH_ID,
        email="tech@example.com",
        display_name="张工",
        password_hash=DEMO_PASSWORD_HASH,
    )
    manager = User(
        id=USER_MANAGER_ID,
        email="manager@example.com",
        display_name="王强",
        password_hash=DEMO_PASSWORD_HASH,
    )
    viewer = User(
        id=USER_VIEWER_ID,
        email="viewer@example.com",
        display_name="只读用户",
        password_hash=DEMO_PASSWORD_HASH,
    )
    other = User(
        id=USER_OTHER_ID,
        email="other@example.com",
        display_name="赵工",
        password_hash=DEMO_PASSWORD_HASH,
    )
    zhao = User(
        id=USER_ZHAO_ID,
        email="zhao@example.com",
        display_name="赵工",
        password_hash=DEMO_PASSWORD_HASH,
    )
    db.add_all([owner, tech, manager, viewer, other, zhao])
    db.flush()

    db.add_all(
        [
            Membership(
                organization_id=demo_org.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            Membership(
                organization_id=demo_org.id,
                user_id=tech.id,
                role="technician",
                status="active",
            ),
            Membership(
                organization_id=demo_org.id,
                user_id=manager.id,
                role="manager",
                status="active",
            ),
            Membership(
                organization_id=demo_org.id,
                user_id=viewer.id,
                role="viewer",
                status="active",
            ),
            Membership(
                organization_id=demo_org.id,
                user_id=zhao.id,
                role="technician",
                status="active",
            ),
            Membership(
                organization_id=north_org.id,
                user_id=other.id,
                role="owner",
                status="active",
            ),
        ]
    )
    db.flush()

    demo_plant = Plant(
        organization_id=demo_org.id,
        code="PLANT-SH-01",
        name="上海演示工厂",
        location="上海（虚构地址）",
        created_by=owner.id,
        updated_by=owner.id,
    )
    north_plant = Plant(
        organization_id=north_org.id,
        code="PLANT-BJ-01",
        name="北京演示工厂",
        location="北京（虚构地址）",
        created_by=other.id,
        updated_by=other.id,
    )
    db.add_all([demo_plant, north_plant])
    db.flush()

    device_specs = [
        (
            "AC-07",
            "螺杆空气压缩机",
            "动力与流体机械",
            "压缩站 Bay03",
            72.4,
            "attention",
            "GX11",
            "SN-DEMO-0007",
        ),
        (
            "P-102",
            "高压离心注水泵",
            "流体动力系统",
            "冷却循环水站",
            84.2,
            "attention",
            "P-102X",
            "SN-DEMO-0102",
        ),
        (
            "CNC-04",
            "数控龙门铣床",
            "精密加工单元",
            "重载加工岛 #3",
            41.0,
            "alert",
            "GMC-4000",
            "SN-DEMO-0004",
        ),
        (
            "WR-09",
            "自动焊接机器人",
            "工业机器人",
            "车身拼装线 #2",
            98.2,
            "running",
            "WR-9",
            "SN-DEMO-0009",
        ),
        (
            "CV-01",
            "重型板链输送线",
            "仓储物流输送",
            "物流转运通道",
            95.0,
            "running",
            "CV-1",
            "SN-DEMO-0001",
        ),
        (
            "AC-08",
            "螺杆空气压缩机",
            "动力与流体机械",
            "压缩站 Bay04",
            88.5,
            "running",
            "GX11",
            "SN-DEMO-0008",
        ),
    ]
    devices: dict[str, Device] = {}
    for code, name, type_, location, health, state, model, serial in device_specs:
        device = Device(
            organization_id=demo_org.id,
            plant_id=demo_plant.id,
            code=code,
            name=name,
            type=type_,
            location=location,
            health=health,
            state=state,
            model=model,
            serial_number=serial,
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.add(device)
        devices[code] = device

    north_device = Device(
        organization_id=north_org.id,
        plant_id=north_plant.id,
        code="NV-01",
        name="北方测试压缩机",
        type="动力与流体机械",
        location="北京演示车间",
        health=90,
        state="running",
        model="NX-1",
        serial_number="SN-NORTH-0001",
        created_by=other.id,
        updated_by=other.id,
    )
    db.add(north_device)
    devices["NV-01"] = north_device
    db.flush()

    drive = DeviceComponent(
        organization_id=demo_org.id,
        device_id=devices["AC-07"].id,
        code="C-DRIVE",
        name="驱动端总成",
        position="驱动端",
        created_by=owner.id,
        updated_by=owner.id,
    )
    db.add(drive)
    db.flush()
    bearing = DeviceComponent(
        organization_id=demo_org.id,
        device_id=devices["AC-07"].id,
        parent_component_id=drive.id,
        code="C-BEARING",
        name="深沟球轴承",
        position="驱动端轴承位",
        created_by=owner.id,
        updated_by=owner.id,
    )
    db.add(bearing)
    db.flush()

    for name, unit in (
        ("rated_power", "kW"),
        ("rated_pressure", "MPa"),
    ):
        db.add(
            DeviceParameter(
                organization_id=demo_org.id,
                device_id=devices["AC-07"].id,
                name=name,
                value=55 if name == "rated_power" else 0.8,
                unit=unit,
                source="nameplate",
                source_ref="铭牌照片 DEMO-NAMEPLATE",
                is_authoritative=True,
                recorded_at=BASE - timedelta(days=30),
                created_by=owner.id,
                updated_by=owner.id,
            )
        )

    for minutes, vibration, temperature in TREND_POINTS:
        recorded = BASE - timedelta(minutes=102 - minutes)
        db.add_all(
            [
                DeviceParameter(
                    organization_id=demo_org.id,
                    device_id=devices["AC-07"].id,
                    component_id=bearing.id,
                    name="vibration",
                    value=vibration,
                    unit="mm/s",
                    source="sensor",
                    source_ref="sensor:AC-07:VIB-01",
                    is_authoritative=True,
                    recorded_at=recorded,
                    created_by=owner.id,
                    updated_by=owner.id,
                ),
                DeviceParameter(
                    organization_id=demo_org.id,
                    device_id=devices["AC-07"].id,
                    component_id=bearing.id,
                    name="temperature",
                    value=temperature,
                    unit="°C",
                    source="sensor",
                    source_ref="sensor:AC-07:TEMP-01",
                    is_authoritative=True,
                    recorded_at=recorded,
                    created_by=owner.id,
                    updated_by=owner.id,
                ),
            ]
        )

    alerts: dict[str, Alert] = {}
    alert_specs = [
        (
            "ALT-0941",
            "AC-07",
            "p1",
            "驱动端轴承高频振动 RMS 严重突破警戒上限",
            "pending",
            tech.id,
            44,
        ),
        (
            "ALT-0938",
            "P-102",
            "p2",
            "排气温度连续接近预警阈值",
            "processing",
            manager.id,
            60,
        ),
        (
            "ALT-0926",
            "CNC-04",
            "p2",
            "主轴负载波动超过基线范围",
            "pending",
            None,
            180,
        ),
        (
            "ALT-0911",
            "AC-08",
            "p3",
            "润滑油压差出现短时下降",
            "closed",
            tech.id,
            1440,
        ),
    ]
    for code, device_code, level, title, status, owner_id, minutes in alert_specs:
        alert = Alert(
            organization_id=demo_org.id,
            device_id=devices[device_code].id,
            code=code,
            level=level,
            title=title,
            status=status,
            owner_user_id=owner_id,
            source="sensor",
            occurred_at=BASE - timedelta(minutes=minutes),
            acknowledged_at=(
                BASE - timedelta(minutes=minutes - 10)
                if status in {"acknowledged", "closed"}
                else None
            ),
            acknowledged_by=(
                owner_id if status in {"acknowledged", "closed"} else None
            ),
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.add(alert)
        alerts[code] = alert

    north_alert = Alert(
        organization_id=north_org.id,
        device_id=north_device.id,
        code="ALT-9001",
        level="p1",
        title="北方测试设备告警",
        status="pending",
        source="sensor",
        occurred_at=BASE - timedelta(minutes=5),
        created_by=other.id,
        updated_by=other.id,
    )
    db.add(north_alert)
    alerts["ALT-9001"] = north_alert
    db.flush()

    diagnosis = Diagnosis(
        organization_id=demo_org.id,
        device_id=devices["AC-07"].id,
        alert_id=alerts["ALT-0941"].id,
        code="DIAG-20250518-0941",
        question="AC-07 振动突然升高，可能是什么原因？",
        conclusion="疑似驱动端深沟球轴承磨损，建议停机检查并更换轴承。",
        risk_level="high",
        confidence=94.6,
        model_source="demo-model-v1",
        evidence={
            "documents": [
                {
                    "name": "Atlas_Copco_GX11_UserManual_RevC.pdf",
                    "version": "RevC",
                    "page": 42,
                    "score": 0.946,
                }
            ]
        },
        status="confirmed",
        confirmed_by=tech.id,
        confirmed_at=BASE - timedelta(minutes=40),
        created_by=tech.id,
        updated_by=tech.id,
    )
    db.add(diagnosis)
    pump_diagnosis = Diagnosis(
        organization_id=demo_org.id,
        device_id=devices["P-102"].id,
        alert_id=alerts["ALT-0938"].id,
        code="DIAG-20250518-0938",
        question="P-102 排气温度持续升高，可能是什么原因？",
        conclusion="疑似机械密封磨损导致温升，建议检查密封与冷却水路。",
        risk_level="medium",
        confidence=88.0,
        model_source="demo-model-v1",
        evidence={
            "documents": [
                {
                    "name": "Pump_P102_Cavitation_Troubleshooting.pdf",
                    "version": "v1.0",
                    "page": 11,
                    "score": 0.88,
                }
            ]
        },
        status="draft",
        created_by=tech.id,
        updated_by=tech.id,
    )
    db.add(pump_diagnosis)
    db.flush()

    work_order_specs = [
        (
            "WO-20250518-01",
            "AC-07",
            "AC-07 驱动端深沟球轴承紧急更换与润滑脂加注",
            "p1",
            "processing",
            tech.id,
            BASE - timedelta(minutes=8),
            BASE - timedelta(minutes=12),
            None,
            alerts["ALT-0941"].id,
            diagnosis.id,
        ),
        (
            "WO-20250518-02",
            "P-102",
            "P-102 机械密封泄漏检查",
            "p2",
            "verifying",
            manager.id,
            BASE - timedelta(minutes=25),
            BASE - timedelta(minutes=90),
            None,
            alerts["ALT-0938"].id,
            None,
        ),
        (
            "WO-20250517-03",
            "CNC-04",
            "CNC-04 主轴动平衡校准",
            "p3",
            "pending",
            zhao.id,
            BASE - timedelta(hours=2),
            None,
            None,
            alerts["ALT-0926"].id,
            None,
        ),
        (
            "WO-20250516-04",
            "AC-08",
            "AC-08 月度定检与油分滤芯检查",
            "p4",
            "completed",
            tech.id,
            BASE - timedelta(days=2),
            BASE - timedelta(days=2, hours=3),
            BASE - timedelta(days=2, hours=1),
            alerts["ALT-0911"].id,
            None,
        ),
    ]
    work_orders = []
    for (
        code,
        device_code,
        title,
        priority,
        status,
        owner_id,
        updated_at,
        started_at,
        closed_at,
        alert_id,
        diagnosis_id,
    ) in work_order_specs:
        order = WorkOrder(
            organization_id=demo_org.id,
            device_id=devices[device_code].id,
            alert_id=alert_id,
            diagnosis_id=diagnosis_id,
            code=code,
            title=title,
            priority=priority,
            status=status,
            owner_user_id=owner_id,
            started_at=started_at,
            closed_at=closed_at,
            created_at=updated_at,
            updated_at=updated_at,
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.add(order)
        work_orders.append(order)

    db.flush()

    db.add(
        MaintenanceRecord(
            organization_id=demo_org.id,
            device_id=devices["AC-08"].id,
            work_order_id=work_orders[3].id,
            alert_id=alerts["ALT-0911"].id,
            record_type="maintenance",
            summary="AC-08 月度定检与油分滤芯检查",
            action_taken="完成月度定检，更换油分滤芯。",
            recorded_by=tech.id,
            recorded_at=BASE - timedelta(days=2, hours=1),
            created_by=tech.id,
            updated_by=tech.id,
        )
    )

    db.add(
        WorkOrder(
            organization_id=north_org.id,
            device_id=north_device.id,
            code="WO-20250518-99",
            title="北方测试设备巡检",
            priority="p1",
            status="pending",
            owner_user_id=other.id,
            created_by=other.id,
            updated_by=other.id,
        )
    )

    db.add_all(
        [
            AuditLog(
                organization_id=demo_org.id,
                actor_user_id=owner.id,
                action="alert.acknowledge",
                entity_type="alert",
                entity_id=alerts["ALT-0911"].id,
                after={"status": "closed"},
            ),
            AuditLog(
                organization_id=demo_org.id,
                actor_user_id=tech.id,
                action="work_order.create",
                entity_type="work_order",
                entity_id=work_orders[2].id,
                after={"code": "WO-20250517-03", "status": "pending"},
            ),
        ]
    )

    db.commit()
    return _collect_ids(db)


def main() -> None:
    from app.db import Base, get_engine, get_sessionmaker

    engine = get_engine()
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
    with get_sessionmaker()() as session:
        ids = seed_demo(session)
    print("已写入虚构演示数据：")
    for org_code, org_id in ids["organizations"].items():
        print(f"  organization {org_code}: {org_id}")
    for email, user_id in ids["users"].items():
        print(f"  user {email}: {user_id}")


if __name__ == "__main__":
    main()
