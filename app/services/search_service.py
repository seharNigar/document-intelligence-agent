import json
import os
import ast
import operator
import re

from dotenv import load_dotenv
from openai import OpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

load_dotenv()


# -------------------------
# Azure OpenAI
# -------------------------

openai_client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT').rstrip('/')}/openai/v1/"
)

EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
)


# -------------------------
# Azure AI Search
# -------------------------

search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_INDEX"),
    credential=AzureKeyCredential(
        os.getenv("AZURE_SEARCH_API_KEY")
    )
)


def generate_embedding(text: str):

    response = openai_client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=text
    )

    return response.data[0].embedding


def upload_document(
    document_id: str,
    document_name: str,
    content: str,
    document_type: str,
    page_number: int,
    metadata: str
):

    embedding = generate_embedding(content)

    document = {
        "id": document_id,
        "documentName": document_name,
        "content": content,
        "documentType": document_type,
        "pageNumber": page_number,
        "metadata": metadata,
        "contentVector": embedding
    }

    result = search_client.upload_documents(
        documents=[document]
    )

    return result


def list_indexed_documents():
    results = search_client.search(
        search_text="*",
        select=["documentName"],
        top=1000
    )
    return sorted({
        result["documentName"]
        for result in results
        if result.get("documentName")
    })


def search_documents(query: str, top_k: int = 3, document_name: str | None = None):
    query_embedding = generate_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields="contentVector",
        kind="vector",
        exhaustive=True
    )
    filter_expression = None

    if document_name:
        filter_expression = f"documentName eq '{document_name}'"

    results = search_client.search(
    search_text=query,
    vector_queries=[vector_query],
    select=[
        "id",
        "documentName",
        "content",
        "documentType",
        "pageNumber",
        "metadata"
    ],
    filter=filter_expression,
    top=top_k
    )

    documents = []

    for result in results:
        documents.append({
            "id": result["id"],
            "documentName": result["documentName"],
            "content": result["content"],
            "documentType": result["documentType"],
            "pageNumber": result["pageNumber"],
            "metadata": result["metadata"],
            "score": result["@search.score"]
        })

    return documents

DOCUMENT_SEARCH_TOOL = {
    "type": "function",
    "name": "search_documents",
    "description": (
        "Search the user's documents for information needed to answer "
        "the question. Use this tool whenever document information "
        "is required."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What information to search for."
            },
            "document_name": {
                "type": ["string", "null"],
                "description": (
                    "The exact document filename to search. "
                    "Use null to search across all documents."
                )
            }
        },
        "required": ["query", "document_name"],
        "additionalProperties": False
    }
}

CALCULATOR_TOOL = {
    "type": "function",
    "name": "calculate",
    "description": (
        "Perform mathematical calculations using numeric values "
        "provided by the document or the user."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": (
                    "A mathematical expression to calculate, "
                    "using numbers only. Example: 1000 / 3100 * 100"
                )
            }
        },
        "required": ["expression"],
        "additionalProperties": False
    }
}

def calculate_expression(expression: str):
    binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }
    unary_operators = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in binary_operators:
            return binary_operators[type(node.op)](
                evaluate(node.left),
                evaluate(node.right),
            )

        if isinstance(node, ast.UnaryOp) and type(node.op) in unary_operators:
            return unary_operators[type(node.op)](evaluate(node.operand))

        raise ValueError("Unsupported expression.")

    try:
        return evaluate(ast.parse(expression, mode="eval").body)
    except (ArithmeticError, SyntaxError, TypeError, ValueError):
        raise ValueError("Unable to calculate expression.") from None


def get_cited_sources(answer: str, source_metadata: list[dict]):
    cited_numbers = {
        int(number)
        for number in re.findall(r"\[Source (\d+)\]", answer)
    }

    return [
        source
        for source in source_metadata
        if source["source"] in cited_numbers
    ]

def generate_answer(
    question: str,
    conversation: list[dict] | None = None,
    document_name: str | None = None
):
    if conversation is None:
        conversation = []

    conversation_text = ""

    if conversation:
        conversation_text = "\n\nConversation history:\n"

        for message in conversation:
            conversation_text += (
                f"{message.get('role', 'user').capitalize()}: "
                f"{message.get('content', '')}\n"
            )

    input_text = (
        f"{conversation_text}\n"
        f"Selected document: {document_name}\n"
        f"Current question: {question}"
    )

    response = openai_client.responses.create(
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        instructions=(
            "You are a document intelligence agent. "

            "You answer questions using the user's documents. "

            "If a selected document is provided and the user asks "
            "about that document, you MUST search only that document. "

            "If the user explicitly asks to compare, search, or retrieve "
            "information from multiple named documents, you may search "
            "each explicitly requested document. "

            "Never search unrelated documents. "

            "Use the search_documents tool whenever you need information "
            "from a document. "

            "Use the document_name parameter to specify the exact document "
            "being searched. When the question explicitly names a document, "
            "use that exact filename even when a different document is selected. "

            "Use the calculate tool whenever mathematical calculation "
            "is required. "

            "Do not perform arithmetic mentally when the calculate tool "
            "can be used. "

            "Do not invent, infer, or assume information that is not "
            "explicitly supported by retrieved documents. "

            "If a document does not explicitly contain a value, say that "
            "the value is not available rather than calculating or assuming it. "

            "Keep answers concise. "

            "Every factual statement derived from a document MUST end with "
            "the relevant [Source X] citation. "

            "Make sure every [Source X] citation corresponds to the "
            "source information provided by the search tool."
        ),
        tools=[
            DOCUMENT_SEARCH_TOOL,
            CALCULATOR_TOOL
        ],
        input=input_text
    )

    source_metadata = []
    source_map = {}

    for _ in range(5):

        tool_outputs = []

        for item in response.output:

            # -----------------------------
            # DOCUMENT SEARCH
            # -----------------------------
            if (
                item.type == "function_call"
                and item.name == "search_documents"
            ):
                arguments = json.loads(item.arguments)

                requested_document = arguments.get("document_name")

                # An explicitly requested filename takes precedence over
                # the currently selected document.
                search_document_name = (
                    requested_document
                    if requested_document
                    else document_name
                )

                documents = search_documents(
                    arguments["query"],
                    top_k=3,
                    document_name=search_document_name
                )

                context_parts = []

                for document in documents:

                    try:
                        metadata = json.loads(
                            document["metadata"]
                        )
                    except (
                        TypeError,
                        json.JSONDecodeError
                    ):
                        metadata = {}

                    source_key = (
                        document["documentName"],
                        document["pageNumber"],
                        metadata.get("chunk_index")
                    )

                    # Create a source only once.
                    if source_key not in source_map:

                        source_number = len(source_metadata) + 1

                        source_map[source_key] = source_number

                        source_metadata.append({
                            "source": source_number,
                            "documentName": document["documentName"],
                            "pageNumber": document["pageNumber"],
                            "chunkIndex": metadata.get(
                                "chunk_index"
                            ),
                            "score": document["score"]
                        })

                    else:
                        source_number = source_map[source_key]

                    context_parts.append(
                        f"[Source {source_number}]\n"
                        f"Document: {document['documentName']}\n"
                        f"Page: {document['pageNumber']}\n"
                        f"Chunk: "
                        f"{metadata.get('chunk_index')}\n"
                        f"Content:\n"
                        f"{document['content']}"
                    )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": "\n\n".join(context_parts)
                })

            # -----------------------------
            # CALCULATOR
            # -----------------------------
            elif (
                item.type == "function_call"
                and item.name == "calculate"
            ):
                arguments = json.loads(item.arguments)

                result = calculate_expression(
                    arguments["expression"]
                )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": str(result)
                })

        # No more tools required
        if not tool_outputs:
            answer = response.output_text
            cited_sources = get_cited_sources(answer, source_metadata)

            if source_metadata and not cited_sources:
                citation_response = openai_client.responses.create(
                    model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
                    previous_response_id=response.id,
                    input=(
                        "Rewrite your previous answer without changing its "
                        "facts. Add [Source X] after every statement based "
                        "on retrieved document information. Use only source "
                        "numbers already provided."
                    )
                )
                answer = citation_response.output_text
                cited_sources = get_cited_sources(
                    answer, source_metadata
                )

            return {
                "answer": answer,
                "sources": cited_sources or source_metadata
            }

        response = openai_client.responses.create(
            model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            previous_response_id=response.id,
            tools=[
                DOCUMENT_SEARCH_TOOL,
                CALCULATOR_TOOL
            ],
            input=tool_outputs
        )

    raise RuntimeError(
        "The model exceeded the maximum number of tool calls."
    )