from datetime import date
from typing import Optional

from pydantic import BaseModel


class InvoiceLineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    vendor: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None

    customer: Optional[str] = None
    customer_address: Optional[str] = None

    currency: Optional[str] = None

    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None

    payment_terms: Optional[str] = None

    payment_status: str | None = None
    amount_paid: float | None = None
    outstanding_balance: float | None = None

    line_items: list[InvoiceLineItem] = []


class InvoiceConfidence(BaseModel):
    invoice_number: Optional[float] = None
    invoice_date: Optional[float] = None
    due_date: Optional[float] = None
    vendor: Optional[float] = None
    customer: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    payment_status: Optional[float] = None
    amount_paid: Optional[float] = None
    outstanding_balance: Optional[float] = None


class InvoiceValidation(BaseModel):
    is_valid: bool
    subtotal_matches_items: bool
    total_matches_calculation: bool
    warnings: list[str] = []

class ProcessedInvoice(BaseModel):
    invoice: InvoiceData
    confidence: InvoiceConfidence
    validation: InvoiceValidation