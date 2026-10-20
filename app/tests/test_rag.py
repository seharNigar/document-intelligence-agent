from app.services.search_service import generate_answer


question = "How much money is still unpaid by the customer?"

result = generate_answer(question)

print("\nQuestion:")
print(question)

print("\nAnswer:")
print(result["answer"])

print("\nSources:")

for source in result["sources"]:
    print(
        f"- {source['documentName']} "
        f"(Page {source['pageNumber']}) "
        f"[Score: {source['score']}]"
    )