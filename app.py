import os

# had to fix the imports do to recent package updates and dependencies.
from dotenv import load_dotenv
from flask import Flask, render_template
from flask import request, jsonify
from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = ChatCohere(cohere_api_key=os.environ["COHERE_API_KEY"])
embeddings = CohereEmbeddings(
    cohere_api_key=os.environ["COHERE_API_KEY"],
    model= "embed-english-v3.0"
)

# load db only if the db directory exists
vectordb = None
if os.path.exists("./db"):
    vectordb = Chroma(persist_directory="./db", embedding_function=embeddings)

chat_history = []

app = Flask(__name__)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

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


def search_knowledgebase(message):
    if vectordb is None:
        return "Knowledgebase not available."
    
    docs = vectordb.similarity_search(message)
    if not docs:
        return "Nothing Found!"

    return "\n\n".join(doc.page_content for doc in docs)

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


@app.route('/kbanswer', methods=['POST'])
def kbanswer():
    message = request.json['message']
    response_message = answer_from_knowledgebase(message)
    return jsonify({'message': response_message}), 200

@app.route('/search', methods=['POST'])
def search():    
    message = request.json["message"]
    response_message = search_knowledgebase(message)
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