"""Read-only operational investigation tools for the ReconGuard AI Investigator."""

import csv
from pathlib import Path
from typing import Any


class InvestigationToolRegistry:
    """Read-only tool registry providing access to operational datasets."""

    def __init__(
        self,
        orders: list[dict[str, Any]] | None = None,
        payments: list[dict[str, Any]] | None = None,
        settlements: list[dict[str, Any]] | None = None,
        invoices: list[dict[str, Any]] | None = None,
        adjustments: list[dict[str, Any]] | None = None,
    ):
        self._orders_by_id = {o["order_id"]: dict(o) for o in (orders or []) if "order_id" in o}
        self._payments_by_id = {p["payment_id"]: dict(p) for p in (payments or []) if "payment_id" in p}
        self._settlements_by_id = {s["settlement_id"]: dict(s) for s in (settlements or []) if "settlement_id" in s}
        self._invoices_by_order_id = {i["order_id"]: dict(i) for i in (invoices or []) if "order_id" in i}

        # Index payments by order_id
        self._payments_by_order_id: dict[str, list[dict[str, Any]]] = {}
        for p in (payments or []):
            oid = p.get("order_id")
            if oid:
                self._payments_by_order_id.setdefault(oid, []).append(dict(p))

        # Index settlements by payment_id
        self._settlements_by_payment_id: dict[str, list[dict[str, Any]]] = {}
        for s in (settlements or []):
            pid = s.get("payment_id")
            if pid:
                self._settlements_by_payment_id.setdefault(pid, []).append(dict(s))

        # Index adjustments by payment_id and order_id
        self._adjustments = [dict(a) for a in (adjustments or [])]

    @classmethod
    def from_csv_directory(cls, data_dir: Path | str) -> "InvestigationToolRegistry":
        """Load operational datasets from CSV files without reading ground truth."""
        dir_path = Path(data_dir)
        gen_dir = dir_path / "generated" if (dir_path / "generated").exists() else dir_path

        def load_csv(filename: str) -> list[dict[str, Any]]:
            filepath = gen_dir / filename
            if not filepath.exists():
                return []
            with open(filepath, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        return cls(
            orders=load_csv("orders.csv"),
            payments=load_csv("payments.csv"),
            settlements=load_csv("settlements.csv"),
            invoices=load_csv("invoices.csv"),
            adjustments=load_csv("adjustments.csv"),
        )

    def lookup_order(self, order_id: str) -> dict[str, Any]:
        """Look up merchant order checkout record by order_id."""
        order = self._orders_by_id.get(order_id)
        if not order:
            return {"found": False, "error": f"Order '{order_id}' not found."}
        return {
            "found": True,
            "order_id": order.get("order_id"),
            "customer_id": order.get("customer_id"),
            "amount": float(order.get("amount", 0.0)),
            "currency": order.get("currency", "INR"),
            "status": order.get("status"),
            "created_at": order.get("created_at"),
        }

    def lookup_payment(self, payment_id: str) -> dict[str, Any]:
        """Look up gateway payment capture record by payment_id."""
        payment = self._payments_by_id.get(payment_id)
        if not payment:
            return {"found": False, "error": f"Payment '{payment_id}' not found."}
        return {
            "found": True,
            "payment_id": payment.get("payment_id"),
            "order_id": payment.get("order_id"),
            "amount": float(payment.get("amount", 0.0)),
            "currency": payment.get("currency", "INR"),
            "status": payment.get("status"),
            "payment_method": payment.get("payment_method"),
            "utr": payment.get("utr"),
            "created_at": payment.get("created_at"),
        }

    def lookup_payments_for_order(self, order_id: str) -> dict[str, Any]:
        """Retrieve all payment records linked to an order_id."""
        payments = self._payments_by_order_id.get(order_id, [])
        return {
            "found": len(payments) > 0,
            "order_id": order_id,
            "count": len(payments),
            "payments": [
                {
                    "payment_id": p.get("payment_id"),
                    "amount": float(p.get("amount", 0.0)),
                    "status": p.get("status"),
                    "payment_method": p.get("payment_method"),
                    "utr": p.get("utr"),
                    "created_at": p.get("created_at"),
                }
                for p in payments
            ],
        }

    def lookup_settlement(self, settlement_id: str) -> dict[str, Any]:
        """Look up bank payout settlement record by settlement_id."""
        settlement = self._settlements_by_id.get(settlement_id)
        if not settlement:
            return {"found": False, "error": f"Settlement '{settlement_id}' not found."}
        return {
            "found": True,
            "settlement_id": settlement.get("settlement_id"),
            "payment_id": settlement.get("payment_id"),
            "amount": float(settlement.get("amount", 0.0)),
            "fee": float(settlement.get("fee", 0.0)),
            "tax": float(settlement.get("tax", 0.0)),
            "net_amount": float(settlement.get("amount", 0.0)) - float(settlement.get("fee", 0.0)) - float(settlement.get("tax", 0.0)),
            "utr": settlement.get("utr"),
            "status": settlement.get("status"),
            "settled_at": settlement.get("settled_at"),
        }

    def lookup_settlements_for_payment(self, payment_id: str) -> dict[str, Any]:
        """Retrieve all settlement records linked to a payment_id."""
        settlements = self._settlements_by_payment_id.get(payment_id, [])
        return {
            "found": len(settlements) > 0,
            "payment_id": payment_id,
            "count": len(settlements),
            "settlements": [
                {
                    "settlement_id": s.get("settlement_id"),
                    "amount": float(s.get("amount", 0.0)),
                    "fee": float(s.get("fee", 0.0)),
                    "tax": float(s.get("tax", 0.0)),
                    "utr": s.get("utr"),
                    "status": s.get("status"),
                    "settled_at": s.get("settled_at"),
                }
                for s in settlements
            ],
        }

    def lookup_invoice(self, order_id: str) -> dict[str, Any]:
        """Look up tax billing invoice for an order_id."""
        invoice = self._invoices_by_order_id.get(order_id)
        if not invoice:
            return {"found": False, "error": f"Invoice for order '{order_id}' not found in billing system."}
        return {
            "found": True,
            "invoice_id": invoice.get("invoice_id"),
            "order_id": invoice.get("order_id"),
            "amount": float(invoice.get("amount", 0.0)),
            "tax_amount": float(invoice.get("tax_amount", 0.0)),
            "status": invoice.get("status"),
            "created_at": invoice.get("created_at"),
        }

    def lookup_adjustments(
        self,
        payment_id: str | None = None,
        order_id: str | None = None,
    ) -> dict[str, Any]:
        """Look up active chargebacks, refunds, or adjustments for a transaction."""
        matching = []
        for adj in self._adjustments:
            rel_id = adj.get("related_id", "")
            if payment_id and rel_id == payment_id:
                matching.append(adj)
            elif order_id and rel_id == order_id:
                matching.append(adj)

        return {
            "found": len(matching) > 0,
            "count": len(matching),
            "adjustments": [
                {
                    "adjustment_id": a.get("adjustment_id"),
                    "type": a.get("type"),
                    "amount": float(a.get("amount", 0.0)),
                    "related_id": a.get("related_id"),
                    "reason": a.get("reason"),
                    "created_at": a.get("created_at"),
                }
                for a in matching
            ],
        }

    def compare_transaction_records(
        self,
        order_id: str,
        payment_id: str | None = None,
        settlement_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare order, payment, and settlement records across financial amounts, references, and dates."""
        order = self.lookup_order(order_id)
        payment = self.lookup_payment(payment_id) if payment_id else {"found": False}
        settlement = self.lookup_settlement(settlement_id) if settlement_id else {"found": False}
        invoice = self.lookup_invoice(order_id)

        amt_order = order.get("amount") if order.get("found") else None
        amt_payment = payment.get("amount") if payment.get("found") else None
        amt_settlement = settlement.get("amount") if settlement.get("found") else None

        amt_diff_pay = round(amt_order - amt_payment, 4) if (amt_order is not None and amt_payment is not None) else None
        amt_diff_set = round(amt_payment - amt_settlement, 4) if (amt_payment is not None and amt_settlement is not None) else None

        utr_payment = payment.get("utr") if payment.get("found") else None
        utr_settlement = settlement.get("utr") if settlement.get("found") else None
        utr_exact_match = (utr_payment == utr_settlement) if (utr_payment and utr_settlement) else False

        return {
            "order_id": order_id,
            "order_amount": amt_order,
            "payment_amount": amt_payment,
            "settlement_amount": amt_settlement,
            "order_payment_amount_difference": amt_diff_pay,
            "payment_settlement_amount_difference": amt_diff_set,
            "payment_utr": utr_payment,
            "settlement_utr": utr_settlement,
            "utr_exact_match": utr_exact_match,
            "invoice_found": invoice.get("found", False),
        }

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with arguments and return structured results."""
        handlers = {
            "lookup_order": lambda a: self.lookup_order(a.get("order_id", "")),
            "lookup_payment": lambda a: self.lookup_payment(a.get("payment_id", "")),
            "lookup_payments_for_order": lambda a: self.lookup_payments_for_order(a.get("order_id", "")),
            "lookup_settlement": lambda a: self.lookup_settlement(a.get("settlement_id", "")),
            "lookup_settlements_for_payment": lambda a: self.lookup_settlements_for_payment(a.get("payment_id", "")),
            "lookup_invoice": lambda a: self.lookup_invoice(a.get("order_id", "")),
            "lookup_adjustments": lambda a: self.lookup_adjustments(
                payment_id=a.get("payment_id"),
                order_id=a.get("order_id"),
            ),
            "compare_transaction_records": lambda a: self.compare_transaction_records(
                order_id=a.get("order_id", ""),
                payment_id=a.get("payment_id"),
                settlement_id=a.get("settlement_id"),
            ),
        }

        if tool_name not in handlers:
            return {"error": f"Invalid tool '{tool_name}'. Tool is not supported."}

        try:
            return handlers[tool_name](arguments)
        except Exception as e:
            return {"error": f"Error executing tool '{tool_name}': {str(e)}"}

    def get_tool_declarations(self) -> list[dict[str, Any]]:
        """Return tool definitions conforming to function-calling schema."""
        return [
            {
                "name": "lookup_order",
                "description": "Look up merchant order checkout record by order_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The unique order identifier (e.g. ORD-000901)"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "lookup_payment",
                "description": "Look up gateway payment capture record by payment_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "payment_id": {"type": "string", "description": "The unique payment identifier (e.g. PAY-000877)"},
                    },
                    "required": ["payment_id"],
                },
            },
            {
                "name": "lookup_payments_for_order",
                "description": "Retrieve all payment records linked to an order_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The order identifier to search payments for"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "lookup_settlement",
                "description": "Look up bank payout settlement record by settlement_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "settlement_id": {"type": "string", "description": "The settlement identifier (e.g. SET-000837)"},
                    },
                    "required": ["settlement_id"],
                },
            },
            {
                "name": "lookup_settlements_for_payment",
                "description": "Retrieve all settlement records linked to a payment_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "payment_id": {"type": "string", "description": "The payment identifier to search settlements for"},
                    },
                    "required": ["payment_id"],
                },
            },
            {
                "name": "lookup_invoice",
                "description": "Look up tax billing invoice for an order_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The order identifier to search invoices for"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "lookup_adjustments",
                "description": "Look up active chargebacks, refunds, or dispute adjustments for a transaction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "payment_id": {"type": "string", "description": "Optional payment ID"},
                        "order_id": {"type": "string", "description": "Optional order ID"},
                    },
                },
            },
            {
                "name": "compare_transaction_records",
                "description": "Compare order, payment, and settlement records across amounts, references, and dates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "Order identifier"},
                        "payment_id": {"type": "string", "description": "Optional payment identifier"},
                        "settlement_id": {"type": "string", "description": "Optional settlement identifier"},
                    },
                    "required": ["order_id"],
                },
            },
        ]

