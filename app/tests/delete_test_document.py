# from app.services.search_service import search_client

# result = search_client.search(
#     search_text="sample_invoice_contoso.pdf",
#     select=["id", "documentName"]
# )

# documents = []

# for doc in result:
#     if doc["documentName"] == "sample_invoice_contoso.pdf":
#         documents.append({
#             "id": doc["id"]
#         })

# if documents:
#     delete_result = search_client.delete_documents(
#         documents=documents
#     )

#     print("Deleted:")
#     print(delete_result)
# else:
#     print("No document found.")


# from app.services.search_service import search_client

# result = search_client.search(
#     search_text="INV-2048",
#     select=["id", "documentName", "metadata"]
# )

# documents = []

# for doc in result:
#     if doc["documentName"] == "sample_invoice_contoso_two.pdf":
#         documents.append({
#             "id": doc["id"]
#         })

# if documents:
#     delete_result = search_client.delete_documents(
#         documents=documents
#     )

#     print("Deleted:")
#     print(delete_result)
# else:
#     print("No sample_invoice_contoso_two.pdf document found.")

from app.services.search_service import search_client

document_ids_to_delete = [
    "c611ea8b-2a75-4883-a3c7-4e5904b1832b",
    "cb01aeff-a2fd-4b8a-aa76-1c48bf7ffe47"
]

documents = []

for document_id in document_ids_to_delete:

    result = search_client.search(
        search_text="*",
        select=["id", "metadata"],
        filter=f"search.ismatch('{document_id}', 'metadata')"
    )

    for doc in result:
        documents.append({
            "id": doc["id"]
        })

print(f"Found {len(documents)} chunks to delete.")

if documents:
    result = search_client.delete_documents(
        documents=documents
    )

    print("Deleted duplicate chunks:")
    print(result)
else:
    print("No duplicate chunks found.")