"""Tests for ReconciliationCase cardinality with payments and settlements junction tables."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.order import Order
from app.models.payment import Payment
from app.models.settlement import Settlement
from app.models.invoice import Invoice
from app.models.reconciliation_case import ReconciliationCase
from app.models.reconciliation_case_payment import ReconciliationCasePayment
from app.models.reconciliation_case_settlement import ReconciliationCaseSettlement


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing junction table relationships."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()


def test_reconciliation_case_links_multiple_payments(db_session: Session):
    """Verify that a single ReconciliationCase can link to multiple payments."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Create order
    order = Order(
        order_id="ORD-TEST-001",
        customer_id="CUST-001",
        amount=2500.0,
        currency="INR",
        created_at=now,
        status="COMPLETED",
    )
    db_session.add(order)

    # 2. Create 2 payments for this order (e.g. duplicate retry scenario)
    p1 = Payment(
        payment_id="PAY-TEST-001",
        order_id="ORD-TEST-001",
        amount=2500.0,
        method="UPI",
        utr="UTR-TEST-001A",
        created_at=now,
        status="SUCCESS",
    )
    p2 = Payment(
        payment_id="PAY-TEST-002",
        order_id="ORD-TEST-001",
        amount=2500.0,
        method="UPI",
        utr="UTR-TEST-001B",
        created_at=now,
        status="SUCCESS",
    )
    db_session.add_all([p1, p2])

    # 3. Create ReconciliationCase
    case = ReconciliationCase(
        case_id="CASE-TEST-001",
        order_id="ORD-TEST-001",
        status="INVESTIGATING",
        confidence=0.5,
        financial_impact=2500.0,
        created_at=now,
    )
    db_session.add(case)
    db_session.commit()

    # 4. Link both payments via junction table
    link1 = ReconciliationCasePayment(case_id="CASE-TEST-001", payment_id="PAY-TEST-001")
    link2 = ReconciliationCasePayment(case_id="CASE-TEST-001", payment_id="PAY-TEST-002")
    db_session.add_all([link1, link2])
    db_session.commit()

    # 5. Verify relationship
    loaded_case = db_session.query(ReconciliationCase).filter_by(case_id="CASE-TEST-001").first()
    assert loaded_case is not None
    assert len(loaded_case.case_payments) == 2
    linked_payment_ids = {cp.payment_id for cp in loaded_case.case_payments}
    assert linked_payment_ids == {"PAY-TEST-001", "PAY-TEST-002"}


def test_reconciliation_case_links_multiple_settlements(db_session: Session):
    """Verify that a single ReconciliationCase can link to multiple settlements."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Create order
    order = Order(
        order_id="ORD-TEST-002",
        customer_id="CUST-002",
        amount=5000.0,
        currency="INR",
        created_at=now,
        status="COMPLETED",
    )
    db_session.add(order)

    # 2. Create 2 settlements (e.g. split payout or adjustment settlement)
    s1 = Settlement(
        settlement_id="SET-TEST-001",
        utr="UTR-SET-001",
        amount=2450.0,
        fees=50.0,
        settled_at=now,
    )
    s2 = Settlement(
        settlement_id="SET-TEST-002",
        utr="UTR-SET-002",
        amount=2450.0,
        fees=50.0,
        settled_at=now,
    )
    db_session.add_all([s1, s2])

    # 3. Create Case
    case = ReconciliationCase(
        case_id="CASE-TEST-002",
        order_id="ORD-TEST-002",
        status="RESOLVED",
        confidence=1.0,
        financial_impact=0.0,
        created_at=now,
    )
    db_session.add(case)
    db_session.commit()

    # 4. Link both settlements via junction table
    link1 = ReconciliationCaseSettlement(case_id="CASE-TEST-002", settlement_id="SET-TEST-001")
    link2 = ReconciliationCaseSettlement(case_id="CASE-TEST-002", settlement_id="SET-TEST-002")
    db_session.add_all([link1, link2])
    db_session.commit()

    # 5. Verify relationship
    loaded_case = db_session.query(ReconciliationCase).filter_by(case_id="CASE-TEST-002").first()
    assert loaded_case is not None
    assert len(loaded_case.case_settlements) == 2
    linked_settle_ids = {cs.settlement_id for cs in loaded_case.case_settlements}
    assert linked_settle_ids == {"SET-TEST-001", "SET-TEST-002"}


def test_duplicate_payment_link_prevented(db_session: Session):
    """Verify that duplicate case-payment links trigger UniqueConstraint IntegrityError."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

    order = Order(order_id="ORD-TEST-003", customer_id="CUST-003", amount=100.0, currency="INR", created_at=now, status="COMPLETED")
    p1 = Payment(payment_id="PAY-TEST-003", order_id="ORD-TEST-003", amount=100.0, method="UPI", utr="UTR-003", created_at=now, status="SUCCESS")
    case = ReconciliationCase(case_id="CASE-TEST-003", order_id="ORD-TEST-003", status="OPEN", confidence=0.0, financial_impact=0.0, created_at=now)

    db_session.add_all([order, p1, case])
    db_session.commit()

    link1 = ReconciliationCasePayment(case_id="CASE-TEST-003", payment_id="PAY-TEST-003")
    db_session.add(link1)
    db_session.commit()

    # Attempting to add duplicate link must fail
    link2 = ReconciliationCasePayment(case_id="CASE-TEST-003", payment_id="PAY-TEST-003")
    db_session.add(link2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_settlement_link_prevented(db_session: Session):
    """Verify that duplicate case-settlement links trigger UniqueConstraint IntegrityError."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

    order = Order(order_id="ORD-TEST-004", customer_id="CUST-004", amount=100.0, currency="INR", created_at=now, status="COMPLETED")
    s1 = Settlement(settlement_id="SET-TEST-004", utr="UTR-004", amount=98.0, fees=2.0, settled_at=now)
    case = ReconciliationCase(case_id="CASE-TEST-004", order_id="ORD-TEST-004", status="OPEN", confidence=0.0, financial_impact=0.0, created_at=now)

    db_session.add_all([order, s1, case])
    db_session.commit()

    link1 = ReconciliationCaseSettlement(case_id="CASE-TEST-004", settlement_id="SET-TEST-004")
    db_session.add(link1)
    db_session.commit()

    # Attempting to add duplicate link must fail
    link2 = ReconciliationCaseSettlement(case_id="CASE-TEST-004", settlement_id="SET-TEST-004")
    db_session.add(link2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

