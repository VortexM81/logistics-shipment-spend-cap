from src.shipment_spend import Shipment, ShipmentLedger


ledger = ShipmentLedger(
    hard_cap_usd=1000.0,
    shipments=[
        Shipment("S-100", 420.0),
        Shipment("S-101", 510.0),
    ],
)
candidate = Shipment("S-102", 100.0)
decision = ledger.can_accept(candidate)
print({"shipment_id": candidate.shipment_id, "accepted": decision.accepted, "remaining_usd": decision.remaining_usd, "reason": decision.reason})
