import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv()


FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
FOUNDRY_AGENT_NAME = os.getenv(
    "FOUNDRY_AGENT_NAME",
    "DocumentIntelligenceAgent"
)
FOUNDRY_AGENT_VERSION = os.getenv("FOUNDRY_AGENT_VERSION", "2")


def get_foundry_openai_client():
    if not FOUNDRY_PROJECT_ENDPOINT:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is not configured.")

    project_client = AIProjectClient(
        endpoint=FOUNDRY_PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
        allow_preview=True
    )

    return project_client.get_openai_client(
        agent_name=FOUNDRY_AGENT_NAME
    )


def ask_foundry_agent(
    question: str,
    conversation_id: str | None = None,
    document_name: str | None = None
):
    client = get_foundry_openai_client()

    if conversation_id:
        conversation = client.conversations.retrieve(conversation_id)
    else:
        conversation = client.conversations.create()

    document_context = (
        f"Selected document: {document_name}\n"
        if document_name
        else "No document is selected.\n"
    )
    response = client.responses.create(
        conversation=conversation.id,
        input=[{
            "role": "user",
            "content": f"{document_context}Question: {question}"
        }]
    )

    return {
        "answer": response.output_text,
        "sources": [],
        "conversation_id": conversation.id
    }