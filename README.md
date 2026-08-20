# 🤖 RAG Document Chatbot

An AI-powered document question-answering chatbot built using **Retrieval-Augmented Generation (RAG)**.

The application allows users to ask questions about a predefined document knowledge base. Relevant information is retrieved from documents using **FAISS vector search**, and **Google Gemini** generates a concise answer based on the retrieved context.

---

## 🚀 Features

- 📄 Document-based question answering
- 🔎 Semantic document retrieval using FAISS
- 🧠 Hugging Face sentence-transformer embeddings
- 🤖 Google Gemini LLM integration
- 🔗 LangChain-based RAG pipeline
- ⚡ FastAPI backend
- 💬 Streamlit chat interface
- 👤 User login/signup
- 🗄️ PostgreSQL database integration
- 💾 Persistent chat history
- 🔄 Conversation history passed to the RAG pipeline
- 📚 Supports multiple knowledge-base documents

---

 🏗️ System Architecture


                    ┌─────────────────────┐
                    │      Streamlit      │
                    │     Frontend UI     │
                    └──────────┬──────────┘
                               │
                               │ HTTP Requests
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐        ┌──────────────────┐
        │   PostgreSQL    │        │   RAG Pipeline   │
        │                 │        │                  │
        │ Users           │        │ FAISS Retriever  │
        │ Chat History    │        │       ↓          │
        └─────────────────┘        │ HuggingFace      │
                                   │ Embeddings       │
                                   │       ↓          │
                                   │ Gemini LLM       │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                      AI Generated
                                         Answer


How RAG Works

The application follows a Retrieval-Augmented Generation workflow:
User Question
      │
      ▼
Streamlit Frontend
      │
      ▼
FastAPI /query
      │
      ▼
Convert Question into Embedding
      │
      ▼
FAISS Similarity Search
      │
      ▼
Retrieve Relevant Documents
      │
      ▼
Combine Retrieved Context
      │
      ▼
Gemini LLM
      │
      ▼
Generate Answer
      │
      ▼
Save Question + Answer
      │
      ▼
PostgreSQL


Step-by-step

The user enters a question through the Streamlit interface.
The question is sent to the FastAPI backend.
The RAG retriever searches the FAISS vector index.
The most relevant document chunks are retrieved.
Retrieved context is provided to the Gemini model.
Gemini generates an answer based on the available context.
The question and generated answer are stored in PostgreSQL.
Previous conversation history can be provided to the RAG chain for contextual responses.


Tech Stack

Technology	Purpose
Python	Core programming language
Streamlit	Frontend / Chat UI
FastAPI	Backend REST API
LangChain	RAG pipeline orchestration
FAISS	Vector similarity search
Hugging Face	Text embeddings
Google Gemini	Large Language Model
PostgreSQL	Users and chat history
Psycopg2	PostgreSQL connection
Uvicorn	FastAPI server

📂 Project Structure
rag-document-chatbot/
│
├── backend/
│   ├── main.py
│   ├── create_index.py
│   ├── create_tabels.py
│   └── requirements.txt
│
├── frontend/
│   └── app.py
│
├── faiss_index/
│   ├── index.faiss
│   └── index.pkl
│
├── knowledge_base/
│   ├── oops_java.pdf
│   └── webscraping.txt
│
├── .gitignore
├── README.md
└── requirements.txt


Knowledge Base

The current knowledge base contains:

oops_java.pdf
webscraping.txt

The FAISS index is generated from the knowledge-base documents and used for semantic retrieval.


⚙️ Installation

1. Clone the repository
git clone https://github.com/Adnan44411/rag-document-chatbot.git
cd rag-document-chatbot
2. Create a virtual environment
python -m venv venv

Activate it on macOS/Linux:

source venv/bin/activate

On Windows:

venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt


🔐 Environment Variables

Create a .env file inside the backend directory:

GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_postgresql_connection_string

Never commit the .env file to GitHub.


Database Setup

Make sure PostgreSQL is running.

Create the required database:

chatbot

Then run:

python backend/create_tabels.py

This creates the required database tables for:

Users
Chat history


▶️ Running the Application

The application requires two processes:

Start FastAPI Backend

From the project root:

cd backend
uvicorn main:app --reload

Backend will run at:

http://127.0.0.1:8000

FastAPI documentation:

http://127.0.0.1:8000/docs
Start Streamlit Frontend

Open another terminal:

cd frontend
streamlit run app.py

Streamlit will provide a local URL in the terminal.



🔌 API Endpoints
GET /

Health/root endpoint.

POST /get_or_create_user

Creates a new user or returns an existing user.

Example request:

{
  "username": "adnan",
  "email": "adnan@example.com"
}
POST /get_history

Retrieves previous conversations for a user.

Example:

{
  "user_id": 22
}
POST /query

Sends a question through the RAG pipeline.

Example:

{
  "user_id": 22,
  "text": "What is inheritance in Java?"
}

Example response:

{
  "answer": "Inheritance allows a subclass to acquire properties and behavior from a superclass."
}
🧠 RAG Components
Embeddings

The project uses:

sentence-transformers/all-MiniLM-L6-v2

to convert text into numerical vector representations.

Vector Store

FAISS is used to perform efficient similarity search over document embeddings.

Retriever

The application retrieves the top 3 relevant results:

search_kwargs={"k": 3}
LLM

Google Gemini is used to generate the final answer using the retrieved context.

Prompt

The RAG prompt provides:

Retrieved document context
Previous chat history
User question

The model is instructed to provide concise answers and respond with:

"I don't know."

when the answer is not available in the provided context.

💾 Conversation History

PostgreSQL stores user conversations.

Each conversation contains:

user_id
prompt
answer

Previous messages are converted into LangChain:

HumanMessage
AIMessage

objects before being passed to the RAG chain.

This allows the application to maintain conversational context.

🔒 Security

Sensitive credentials are stored in environment variables rather than source code.

The .env file is excluded through .gitignore.

For production deployment, additional security measures should be implemented, including:

Authentication and authorization
Restricted CORS origins
API rate limiting
Secure secret management
Database connection pooling
HTTPS
🚧 Future Improvements

Potential improvements include:

📤 User document upload
🧩 Automatic document chunking and indexing
🔐 JWT-based authentication
🌐 Production deployment
🗂️ Multiple document collections per user
📊 Retrieval evaluation and monitoring
⚡ Streaming LLM responses
🧠 Improved conversational memory
🔍 Hybrid keyword + semantic search
🧪 Automated backend tests
🎯 Learning Objectives

This project demonstrates practical implementation of:

Retrieval-Augmented Generation
Vector embeddings
Semantic search
Vector databases
LLM integration
LangChain
REST API development
PostgreSQL database integration
Conversational AI
Frontend-backend integration
👨‍💻 Author

Adnan Adil

GitHub:
https://github.com/Adnan44411

⭐ Project

If you find this project useful, consider giving the repository a ⭐ on GitHub.
