# ThinkBot — Implementation Notes

## Structural Changes for Updated Package Versions

The original starter scaffold assumed an older LangChain API surface (`langchain_classic`, `RetrievalQA`, legacy chain constructors). By the time this project was implemented, the LangChain ecosystem had undergone a major reorganization:

| Area | Original Spec / Older API | Implemented With |
|------|--------------------------|-----------------|
| LLM import | `from langchain.chat_models import ChatCohere` | `from langchain_cohere import ChatCohere, CohereEmbeddings` |
| Vector store import | `from langchain.vectorstores import Chroma` | `from langchain_chroma import Chroma` |
| Chain construction | `RetrievalQA.from_chain_type(...)` | Manual retriever → prompt → LLM → parser chain using LCEL (`|` pipe syntax) |
| Output parsing | Built-in to chain type | Explicit `StrOutputParser()` from `langchain_core.output_parsers` |
| Prompt templates | `PromptTemplate` + `ConversationBufferMemory` | `ChatPromptTemplate` + `MessagesPlaceholder` from `langchain_core.prompts` |
| Conversation memory | `ConversationBufferMemory` object | Manual `chat_history` list of `HumanMessage` / `AIMessage` objects |
| Embeddings | `CohereEmbeddings` from `langchain_community` | `CohereEmbeddings` from `langchain_cohere` (v0.3+) |
| Chroma persistence | `Chroma(persist_directory=...).persist()` | `Chroma(persist_directory=...)` — persistence is automatic in chromadb 0.5+ |

The `requirements.txt` reflects these changes with version-pinned modern packages (`langchain>=0.3.0`, `langchain-cohere>=0.3.0`, `langchain-chroma>=0.1.4`, `chromadb>=0.5.0`, `cohere>=5.0.0`, `pydantic>=2`). All chain-building was rewritten using **LangChain Expression Language (LCEL)** — the `prompt | llm | parser` pipe pattern that replaced the legacy chain classes.

---

## US-01 — Answer as Chatbot

**Requirement:** Respond to general user questions using a LangChain prompt template and the Cohere LLM. Optionally maintain conversation memory.

**Solution:**

`answer_as_chatbot()` builds a `ChatPromptTemplate` with three components:
1. A system message establishing the assistant's persona ("You are a helpful assistant called Thinkbot.")
2. A `MessagesPlaceholder` for injecting the running `chat_history` list.
3. A human turn placeholder for the current `{input}`.

The chain `prompt | llm` is invoked with the message and history. After each response, both a `HumanMessage` and an `AIMessage` are appended to the module-level `chat_history` list, giving the model full conversational context across turns. The raw `.content` of the response is returned and sent back to the frontend as JSON.

---

## US-02 — Answer from Knowledgebase

**Requirement:** Allow users to ask questions answered from a pre-built document knowledge base using Chroma and Cohere embeddings.

**Solution:**

At startup, if the `./db` directory exists, a `Chroma` vector store is loaded with `CohereEmbeddings` (model `embed-english-v3.0`). In `answer_from_knowledgebase()`:

1. `vectordb.as_retriever().invoke(message)` fetches the most relevant document chunks.
2. `format_docs()` joins their `page_content` into a single context string.
3. A `ChatPromptTemplate` injects that context into a system message: *"Answer the question using only the following context."*
4. The LCEL chain `prompt | llm | StrOutputParser()` generates and returns a grounded answer.

This replaces the `RetrievalQA.from_chain_type()` approach from the spec, which is no longer part of the maintained LangChain API, with an equivalent manual RAG pipeline that is both more transparent and fully compatible with the current library version.

Collab was utilized to set up the necessary tools for question-answering. It converted the animal_life_and_intelligence.txt file into numerical representations called embeddings, creates a search index for the documents, and sets up a retrieval-based question-answering system using a specific type of chain (RetrievalQA).  Note: because the Quantam Computing text was already split, that data was also included in the final db.

---

## US-03 — Search Knowledgebase

**Requirement:** Return the raw source documents most relevant to a user's query, without generating an LLM response.

**Solution:**

`search_knowledgebase()` calls `vectordb.similarity_search(message)` directly against the Chroma store. The resulting `Document` objects have their `page_content` joined with double newlines and returned as plain text. No LLM call is made — this is a pure vector similarity lookup, useful for letting users see the source material the chatbot draws from. A guard clause returns `"Nothing Found!"` when the search yields no results.

---

## US-04 — Improved User Interface

**Requirement:** Give the chatbot a name, a visually appealing design, and user-friendly features (auto-scroll, clear button, loading indicator).

**Solution:**

The UI was themed around **"The Brain Bot"** (an Animaniacs homage). Key implementation details:

- **`templates/index.html`:** Bootstrap 4.5 grid with a fixed-height scrollable `#chat-container`, a mode dropdown (`answer` / `kbanswer` / `search`), a text input, Send and Clear buttons, and mascot images flanking the chat window.
- **`static/style.css`:** A dark theme using navy/deep-blue backgrounds (`#1a1a2e`, `#16213e`) and purple accents (`#9b59b6`). User messages are right-aligned with a purple bubble; assistant messages are left-aligned with a blue bubble. A CSS pulse animation serves as the loading indicator.
- **`static/main.js`:** `sendMessage()` reads the dropdown to select the correct endpoint (`/answer`, `/kbanswer`, `/search`), shows a loading indicator div, sends an `XMLHttpRequest` POST, then calls `displayMessage()` on the response. `displayMessage()` creates a styled div with the sender label, message text, and timestamp, appends it to `#chat-container`, and calls `scrollTop = scrollHeight` for auto-scroll. The Clear button empties the container's innerHTML.

---

## US-05 — Deployment

**Requirement:** Deploy the application on Render.

**Solution:**

The application is configured for Render using Gunicorn as the WSGI server:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Environment variables set in Render:** `COHERE_API_KEY` and `PYTHON_VERSION=3.13.7`

The `COHERE_API_KEY` is never committed — it is read at runtime via `python-dotenv` from the host environment. The `./db` Chroma database is committed to the repository (within GitHub's 25 MB file size limit) so it is available in the deployed environment without a separate build step.

---

## Application Architecture & Patterns

### Flask + JSON API
The backend is a thin Flask app that exposes three `POST` endpoints (`/answer`, `/kbanswer`, `/search`) each accepting `{"message": "..."}` JSON and returning `{"message": "..."}` JSON. The frontend communicates exclusively through these endpoints, making the client/server boundary clean and the backend independently testable.

### Retrieval-Augmented Generation (RAG)
US-02 and US-03 implement the RAG pattern: user queries are embedded, matched against a pre-indexed vector store (Chroma), and the retrieved chunks are injected as context into the LLM prompt. This grounds the model's responses in specific source material rather than relying on parametric knowledge alone.

### LangChain Expression Language (LCEL)
All chains are built with the `|` pipe operator: `prompt | llm | parser`. This replaces the deprecated legacy chain classes (`LLMChain`, `RetrievalQA`) with composable, inspectable runnables that are the current idiomatic approach in LangChain 0.3+.

### In-Memory Conversation History
Conversational context for the chatbot mode is maintained as a module-level Python list of `HumanMessage` / `AIMessage` objects. This is injected into the prompt via `MessagesPlaceholder`, giving the LLM multi-turn context without a database or session layer. The trade-off is that history is per-process and resets on server restart.

### Test Isolation via Mocking
`conftest.py` uses pytest fixtures with `unittest.mock.patch` to replace `app.llm.invoke` and `app.vectordb` with controlled fakes before any test runs. This means the full test suite executes offline without any Cohere API calls or disk I/O against the Chroma database, keeping tests fast and deterministic.

## Future Enhancements
1. UI: Add "Thinking..." or some other visual cue that the request is in process.
1. Error Handling: Capture unsucessful responses and fail gracefully, informing the user to please try again.