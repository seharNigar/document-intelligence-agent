import os

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient


load_dotenv()


endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")


client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)


def analyze_invoice(file_bytes: bytes):

    poller = client.begin_analyze_document(
        "prebuilt-invoice",
        body=file_bytes
    )

    result = poller.result()

    if not result.documents:
        return {
            "message": "No invoice information found"
        }

    invoice = result.documents[0]
    fields = invoice.fields

    items = []

    items_field = fields.get("Items")

    if items_field and items_field.value_array:

        for item in items_field.value_array:

            item_fields = item.value_object

            items.append({
                "description": get_field_value(item_fields, "Description"),
                "quantity": get_field_value(item_fields, "Quantity"),
                "unit_price": get_field_value(item_fields, "UnitPrice"),
                "amount": get_field_value(item_fields, "Amount")
            })

    return {
        "vendor": get_field_value(fields, "VendorName"),
        "invoice_number": get_field_value(fields, "InvoiceId"),
        "invoice_date": get_field_value(fields, "InvoiceDate"),
        "due_date": get_field_value(fields, "DueDate"),
        "customer": get_field_value(fields, "CustomerName"),
        "subtotal": get_field_value(fields, "SubTotal"),
        "tax": get_field_value(fields, "TotalTax"),
        "total": get_field_value(fields, "InvoiceTotal"),
        "items": items
    }


def get_field_value(fields, field_name):

    field = fields.get(field_name)

    if not field:
        return None

    return field.content

def analyze_document_layout(file_bytes: bytes):

    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=file_bytes
    )

    result = poller.result()

    tables = []

    if result.tables:
        for table in result.tables:

            rows = []

            for row_index in range(table.row_count):
                row = []

                for cell in table.cells:
                    if cell.row_index == row_index:
                        row.append(cell.content)

                rows.append(row)

            tables.append({
                "row_count": table.row_count,
                "column_count": table.column_count,
                "rows": rows
            })

    return {
        "content": result.content,
        "tables": tables
    }

def analyze_general_document(file_bytes: bytes):

    poller = client.begin_analyze_document(
        "prebuilt-document",
        body=file_bytes
    )

    result = poller.result()

    return {
        "content": result.content,
        "documents": len(result.documents),
        "tables": len(result.tables) if result.tables else 0
    }