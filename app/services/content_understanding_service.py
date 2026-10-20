import os

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentunderstanding import ContentUnderstandingClient

load_dotenv()

endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
key = os.getenv("CONTENTUNDERSTANDING_KEY")

client = ContentUnderstandingClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)


def analyze_invoice_with_content_understanding(file_bytes: bytes):

    poller = client.begin_analyze_binary(
        analyzer_id="invoice_intelligence_analyzer_v2",
        binary_input=file_bytes
    )

    result = poller.result()

    content = result.contents[0]

    fields = {}

    for field_name, field_data in content.fields.items():

        value = extract_field_value(field_data)

        fields[field_name] = {
            "value": value,
            "confidence": field_data.confidence
        }

    invoice = build_invoice_data(fields)
    confidence = build_invoice_confidence(fields)

    validation = validate_invoice(invoice)

    confidence_warnings = add_confidence_warnings(confidence)

    validation["warnings"].extend(confidence_warnings)

    return {
        "invoice": invoice,
        "confidence": confidence,
        "validation": validation
    }

def extract_field_value(field_data):

    value_string = getattr(field_data, "value_string", None)
    if value_string is not None:
        return value_string

    value_number = getattr(field_data, "value_number", None)
    if value_number is not None:
        return value_number

    value_boolean = getattr(field_data, "value_boolean", None)
    if value_boolean is not None:
        return value_boolean

    value_date = getattr(field_data, "value_date", None)
    if value_date is not None:
        return value_date

    value_object = getattr(field_data, "value_object", None)
    if value_object is not None:
        return {
            key: extract_field_value(value)
            for key, value in value_object.items()
        }

    value_array = getattr(field_data, "value_array", None)
    if value_array is not None:
        return [
            extract_field_value(item)
            for item in value_array
        ]

    return None

def get_field_value(fields, field_name):
    field = fields.get(field_name)

    if not field:
        return None

    return field["value"]


def get_confidence(fields, field_name):
    field = fields.get(field_name)

    if not field:
        return None

    return field["confidence"]

def build_invoice_data(fields):

    line_items = []

    raw_line_items = fields.get("line_items")

    if raw_line_items:
        items = raw_line_items["value"]

        if items:
            line_items = items

    return {
        "invoice_number": get_field_value(fields, "invoice_number"),
        "invoice_date": get_field_value(fields, "invoice_date"),
        "due_date": get_field_value(fields, "due_date"),

        "vendor": get_field_value(fields, "vendor_name"),
        "vendor_address": get_field_value(fields, "vendor_address"),
        "vendor_tax_id": get_field_value(fields, "vendor_tax_id"),

        "customer": get_field_value(fields, "customer_name"),
        "customer_address": get_field_value(fields, "customer_address"),

        "currency": normalize_currency(get_field_value(fields, "currency")),
        "subtotal": get_field_value(fields, "subtotal"),
        "tax": get_field_value(fields, "tax_amount"),
        "discount": get_field_value(fields, "discount_amount"),
        "total": get_field_value(fields, "total_amount"),

        "payment_terms": get_field_value(fields, "payment_terms"),

        "payment_status": get_field_value(fields, "payment_status"),
        "amount_paid": get_field_value(fields, "amount_paid"),
        "outstanding_balance": get_field_value(fields, "outstanding_balance"),

        "line_items": line_items
    }

def build_invoice_confidence(fields):

    return {
        "invoice_number": get_confidence(fields, "invoice_number"),
        "invoice_date": get_confidence(fields, "invoice_date"),
        "due_date": get_confidence(fields, "due_date"),

        "vendor": get_confidence(fields, "vendor_name"),
        "customer": get_confidence(fields, "customer_name"),

        "subtotal": get_confidence(fields, "subtotal"),
        "tax": get_confidence(fields, "tax_amount"),
        "discount": get_confidence(fields, "discount_amount"),
        "total": get_confidence(fields, "total_amount"),
        "payment_status": get_confidence(fields, "payment_status"),
        "amount_paid": get_confidence(fields, "amount_paid"),
        "outstanding_balance": get_confidence(
            fields, "outstanding_balance"
        )
    }

def validate_invoice(invoice):
    warnings = []

    subtotal_matches_items = True
    total_matches_calculation = True

    # Check line items against subtotal
    if invoice["line_items"] and invoice["subtotal"] is not None:
        items_total = sum(
            item.get("amount", 0) or 0
            for item in invoice["line_items"]
        )

        subtotal_matches_items = abs(
            items_total - invoice["subtotal"]
        ) < 0.01

        if not subtotal_matches_items:
            warnings.append(
                "Line item total does not match subtotal."
            )

    # Check subtotal + tax - discount = total
    if (
        invoice["subtotal"] is not None
        and invoice["tax"] is not None
        and invoice["discount"] is not None
        and invoice["total"] is not None
    ):
        calculated_total = (
            invoice["subtotal"]
            + invoice["tax"]
            - invoice["discount"]
        )

        total_matches_calculation = abs(
            calculated_total - invoice["total"]
        ) < 0.01

        if not total_matches_calculation:
            warnings.append(
                "Subtotal, tax, and discount do not match total."
            )

    is_valid = (
        subtotal_matches_items
        and total_matches_calculation
    )

    return {
        "is_valid": is_valid,
        "subtotal_matches_items": subtotal_matches_items,
        "total_matches_calculation": total_matches_calculation,
        "warnings": warnings
    }

def add_confidence_warnings(confidence):
    warnings = []

    threshold = 0.80

    for field_name, score in confidence.items():
        if score is not None and score < threshold:
            warnings.append(
                f"Low confidence for {field_name}: {score:.2f}"
            )

    return warnings

def normalize_currency(currency):
    currency_map = {
        "£": "GBP",
        "$": "USD",
        "€": "EUR",
        "¥": "JPY"
    }

    if not currency:
        return None

    return currency_map.get(currency, currency)