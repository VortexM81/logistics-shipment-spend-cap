from src.shipment_spend import Shipment, ShipmentEvent, ShipmentLedger


def test_candidate_is_rejected_before_dispatch_when_monthly_cap_would_be_crossed():
    ledger = ShipmentLedger(
        hard_cap_usd=1000.0,
        shipments=[
            Shipment("S-100", 420.0, events=(ShipmentEvent("picked_up", "2026-01-01"),)),
            Shipment("S-101", 510.0),
        ],
    )

    decision = ledger.can_accept(Shipment("S-102", 100.0))

    assert decision.accepted is False
    assert decision.projected_usd == 1030.0
    assert decision.remaining_usd == -30.0
    assert decision.reason == "monthly cap would be exceeded"
