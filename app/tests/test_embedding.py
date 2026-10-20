

# from app.services.search_service import generate_embedding


# text = """
# Invoice INV-1235
# Invoice date: 2026-09-15
# Customer: ABC Ltd
# Total amount: $2450
# Outstanding amount: $1000
# """


# embedding = generate_embedding(text)

# print("Embedding generated successfully!")
# print("Dimensions:", len(embedding))
# print("First 5 values:", embedding[:5])


from app.services.search_service import upload_document

result = upload_document(
    document_id="INV-1235",
    document_name="invoice-1235.json",
    content="""
Invoice Number: INV-1235
Invoice Date: 2026-09-15
Customer: ABC Ltd
Total Amount: $2450
Outstanding Amount: $1000
""",
    document_type="invoice",
    page_number=1,
    metadata='{"source": "document-intelligence"}'
)

print("Upload completed!")
print(result)