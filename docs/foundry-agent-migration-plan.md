# Microsoft Foundry Agent Migration Plan

## Status

Planning only. No application code, dependencies, Azure resources, or deployment configuration have been changed for this migration.

## Goal

Replace the application's direct Azure OpenAI Responses API orchestration with a Microsoft Foundry agent and introduce Foundry evaluations, while preserving the current invoice upload, Azure AI Search, source citations, and browser API contract.

## Recommended Architecture

Use a Microsoft Foundry hosted agent implemented in Python.

This is preferred over a prompt-only agent because it preserves the application-owned behavior that already exists:

- Azure AI Search retrieval against the existing index.
- Exact selected-document filtering.
- Safe calculator execution.
- Structured source metadata and citation mapping.
- Foundry-managed conversation memory through agent threads.

The FastAPI application remains responsible for the user interface, document extraction/indexing, and calling the deployed agent. Foundry becomes responsible for reasoning, tool selection, response generation, and conversation memory through agent threads.

## Planned Changes

### 1. Add a Foundry hosted-agent project

- Create hosted-agent source and configuration in the repository.
- Move the current document-agent instructions from `app/services/search_service.py` into agent instructions.
- Configure the agent with the existing Azure OpenAI chat model deployment or a selected Foundry project deployment.
- Add Foundry project endpoint, agent identity, and authentication configuration through environment variables or managed identity configuration.

### 2. Convert local functions into agent tools

- Expose the existing `search_documents` behavior as a hosted-agent tool backed by Azure AI Search.
- Preserve the selected-document restriction so a question does not retrieve unrelated documents.
- Expose the AST-restricted `calculate_expression` behavior as a hosted-agent tool.
- Return structured source data containing document name, page number, chunk index, and score so the API can retain its current `sources` response contract.

### 3. Replace direct model orchestration

- Replace the direct `openai_client.responses.create(...)` loop in `app/services/search_service.py`.
- Update `POST /api/ask` to create a Foundry thread for a new chat or continue the Foundry thread identified by the existing `conversation_id` field.
- Store no chat messages in SQLite. The `conversation_id` returned to the browser will be the Foundry thread identifier.
- Add the selected document name to each new thread's initial context and send it with later messages when the selection changes, so document-scoping remains explicit.
- Convert the agent result into the existing API response fields:
  - `answer`
  - `sources`
  - `conversation_id`
  - `document_name`
- Remove the SQLite conversation models, database initialization, and local message persistence after the agent-thread path is validated.
- Define thread ownership, retention, deletion, and reset behavior. The UI's "new conversation" action will discard the active thread ID and create a new Foundry thread on the next question.

### 4. Preserve document ingestion

The following components can remain materially unchanged:

- Azure Content Understanding invoice extraction.
- Invoice validation and confidence warnings.
- Conversion of structured invoice data to JSON.
- Chunking and embedding generation.
- Azure AI Search indexing.
- Existing upload UI and structured invoice details display.

The Azure AI Search schema and metadata will be reviewed to confirm the hosted agent tool can return all citation fields consistently.

### 5. Add Foundry evaluations

Create an evaluation dataset with representative invoices, questions, expected facts, and expected source references.

The evaluation set should cover:

- Invoice totals, paid amounts, and outstanding balances.
- Questions requiring calculator use.
- Missing or unavailable values.
- Low-confidence extraction warnings.
- Selected-document boundaries.
- Explicit multi-document comparison requests.
- Grounded answers and correct citations.
- Cases where the agent must not invent document facts.

Configure Foundry evaluation runs to measure at least:

- Response relevance.
- Groundedness/faithfulness to retrieved content.
- Citation correctness.
- Tool-use and document-scoping behavior.
- Safety against unsupported assertions.

Define acceptance thresholds and store results so future instruction, model, or tool changes can be evaluated for regression.

### 6. Add debugging and tests

- Add VS Code debug/task configuration for the Foundry Toolkit Agent Inspector.
- Add focused unit tests for search filtering, citation mapping, calculator safety, agent-response mapping, thread creation, thread continuation, and thread reset behavior.
- Add an opt-in integration test path against non-production Azure resources.

### 7. Update dependencies and documentation

- Add the required Foundry agent and evaluation SDK packages.
- Add `debugpy` if required by the Foundry debugging configuration.
- Document local setup, required Foundry resources, configuration variables, deployment, and evaluation workflow.
- Preserve backward compatibility for the browser UI by keeping the `/api/ask` response shape stable.
- Document Foundry thread retention and data-handling behavior, including how a user starts a new conversation and how existing conversation records are retired.

## Decision Required Before Implementation

Select the Microsoft Foundry project and model deployment that will host the agent.

The Foundry Toolkit project/model discovery was not completed, so the following information remains unknown:

- Whether a Foundry project is already selected in VS Code.
- The project endpoint and resource group.
- The available model deployments.
- Whether the existing Azure OpenAI chat deployment should be reused or a Foundry-managed deployment selected.

## Alternative Considered

A Foundry prompt agent connected directly to Azure AI Search would require less custom hosting, but it risks changing current behavior around exact document filtering, calculator safety, and structured citations. The hosted-agent approach is the recommended path for this application.
