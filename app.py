import os

# had to fix the imports do to recent package updates and dependencies.
# --- Dependencies ---
# langchain_cohere: Cohere-specific LLM and embedding wrappers (split from langchain_community in v0.3+)
# langchain_chroma: Chroma vector store integration (replaces langchain_community.vectorstores.Chroma)
# langchain_core.prompts: ChatPromptTemplate builds structured multi-role prompts; MessagesPlaceholder
#   injects a list of Message objects into the prompt at runtime (used for conversation history)
# langchain_core.messages: HumanMessage / AIMessage are the typed objects that make up chat history
# langchain_core.output_parsers: StrOutputParser unwraps the LLM's response object into a plain string
from dotenv import load_dotenv
from flask import Flask, render_template
from flask import request, jsonify
from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# --- LLM and Embedding model setup ---
# Both objects share the same API key but serve different purposes:
#   llm        → generates text (used in answer_as_chatbot and answer_from_knowledgebase)
#   embeddings → converts text to vectors (used only when loading/querying the Chroma DB)
# These are module-level singletons — initialized once at startup, reused across requests.
llm = ChatCohere(cohere_api_key=os.environ["COHERE_API_KEY"])
embeddings = CohereEmbeddings(
    cohere_api_key=os.environ["COHERE_API_KEY"],
    model= "embed-english-v3.0"
)

# load db only if the db directory exists
# --- Vector database (RAG knowledge base) ---
# Chroma loads a pre-built vector store from the ./db directory.
# The DB was created separately (via a Colab notebook) by embedding source documents
# with CohereEmbeddings and persisting them to disk.
# vectordb is None when ./db doesn't exist — all KB functions guard against this.
vectordb = None
if os.path.exists("./db"):
    vectordb = Chroma(persist_directory="./db", embedding_function=embeddings)
    # Debugging statements
    #print("Collections in db:", vectordb._client.list_collections())
    #print("doc count:", vectordb._collection.count())
    #print("default collection:", vectordb._collection_name)
    

chat_history = []

app = Flask(__name__)

# Joins retrieved Document objects into a single context string for the LLM prompt.
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# RAG pattern: retrieve relevant document chunks → inject as context → generate a grounded answer.
# The LLM is instructed to answer *only* from the provided context, reducing hallucination.
def answer_from_knowledgebase(message):
    if vectordb is None:
        return "Knowledgebase not available."
    docs = vectordb.as_retriever().invoke(message)
    context = format_docs(docs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question using only the following context:\n\n{context}"),
        ("human", "{question}")
    ])
    chain = prompt | llm | StrOutputParser()

    return chain.invoke({"context": context, "question": message})

# Pure vector similarity search — no LLM call. Returns the raw source document chunks
# so the user can read the original text the chatbot would draw from.
def search_knowledgebase(message):
    if vectordb is None:
        return "Knowledgebase not available."
    
    # print (message)

    docs = vectordb.similarity_search(message)

    # print(f"len docs: {len(docs)}")

    if not docs:
        return "Nothing Found!"

    return "\n\n".join(doc.page_content for doc in docs)

# Conversational chatbot using LangChain Expression Language (LCEL).
# MessagesPlaceholder injects the running chat_history list so the LLM sees prior turns.
# Pattern: build prompt → pipe to llm → response; then manually append both sides to history.
# Note: chat_history is module-level (in-memory) — it resets if the server restarts.
def answer_as_chatbot(message):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant called Thinkbot."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    chain=prompt | llm
    response = chain.invoke({"input":message, "chat_history": chat_history})
    chat_history.append(HumanMessage(content=message))
    chat_history.append(AIMessage(content=response.content))
    return response.content

# --- Flask API routes ---
# Each route accepts a POST with JSON body {"message": "..."} and returns {"message": "..."}.
# The frontend (main.js) selects which endpoint to call based on the dropdown value.
@app.route('/kbanswer', methods=['POST'])
def kbanswer():
    message = request.json['message']
    try:
        response_message = answer_from_knowledgebase(message)
    except:
        response_message = 'Error: Could not reach the server.'
        print("An exception occurred")
    return jsonify({'message': response_message}), 200

@app.route('/search', methods=['POST'])
def search():    
    message = request.json["message"]
    try:
        response_message = search_knowledgebase(message)
    except:
        response_message = 'Error: Could not reach the server.'
        print("An exception occurred")
    return jsonify({'message': response_message}), 200

@app.route('/answer', methods=['POST'])
def answer():
    message = request.json['message']
    
    # Generate a response
    response_message = answer_as_chatbot(message)
    
    # Return the response as JSON
    return jsonify({'message': response_message}), 200

@app.route("/")
def index():
    return render_template("index.html", title="")

if __name__ == "__main__":
    app.run()