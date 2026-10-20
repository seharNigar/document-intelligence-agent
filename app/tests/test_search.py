from app.services.search_service import search_documents


query = "How much money is still unpaid by the customer?"

results = search_documents(query)

print("\nSearch results:\n")

for result in results:
    print("Document:", result["documentName"])
    print("Score:", result["score"])
    print("Content:")
    print(result["content"])
    print("-" * 50)