import os
import psycopg2

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastembed import TextEmbedding

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DB_URL:
    raise ValueError("DATABASE_URL is not set in .env")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY


# ============================================================
# DATABASE
# ============================================================

def get_db_conn():
    return psycopg2.connect(DB_URL)


# ============================================================
# FASTEMBED WRAPPER
# ============================================================

class FastEmbedEmbeddings(Embeddings):

    def __init__(self):
        self.model = TextEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

    def embed_documents(self, texts):
        return [vector.tolist() for vector in self.model.embed(texts)]

    def embed_query(self, text):
        return next(self.model.embed([text])).tolist()


# ============================================================
# RAG SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAISS_PATH = os.path.join(BASE_DIR, "faiss_index")

print("Loading FastEmbed...")

embeddings = FastEmbedEmbeddings()

print("Loading FAISS index...")

db = FAISS.load_local(
    FAISS_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

print("FAISS index loaded successfully.")

retriever = db.as_retriever(
    search_kwargs={"k": 3}
)


# ============================================================
# GEMINI
# ============================================================

print("Loading Gemini...")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash"
)

print("Gemini loaded.")


# ============================================================
# RAG PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a helpful assistant.

Use the provided context to answer the user's question.

Keep the answer within a maximum of three sentences.

If you don't know the answer from the context, simply say:
"I don't know."

Context:
{context}

Chat History:
{chat_history}
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)


# ============================================================
# RAG CHAIN
# ============================================================

qa_chain = create_stuff_documents_chain(
    llm,
    prompt
)

rag_chain = create_retrieval_chain(
    retriever,
    qa_chain
)

print("RAG chain created successfully.")


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI()


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QueryRequest(BaseModel):
    user_id: int
    text: str


class HistoryRequest(BaseModel):
    user_id: int


class UserRequest(BaseModel):
    username: str
    email: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def read_root():
    return {
        "message": "RAG Chatbot API is running",
        "docs": "/docs"
    }


# ============================================================
# LOGIN / SIGNUP
# ============================================================

@app.post("/get_or_create_user")
def get_or_create_user(req: UserRequest):

    conn = get_db_conn()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT id, username, email
            FROM users
            WHERE username = %s
            """,
            (req.username,)
        )

        user_row = cur.fetchone()

        if user_row:

            return {
                "user_id": user_row[0],
                "username": user_row[1],
                "email": user_row[2]
            }

        cur.execute(
            """
            INSERT INTO users (username, email)
            VALUES (%s, %s)
            RETURNING id
            """,
            (req.username, req.email)
        )

        user_id = cur.fetchone()[0]

        conn.commit()

        return {
            "user_id": user_id,
            "username": req.username,
            "email": req.email
        }

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()


# ============================================================
# GET CHAT HISTORY
# ============================================================

@app.post("/get_history")
def get_history(req: HistoryRequest):

    conn = get_db_conn()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT prompt, answer
            FROM chat_history
            WHERE user_id = %s
            ORDER BY id ASC
            """,
            (req.user_id,)
        )

        history = cur.fetchall()

        formatted_history = []

        for prompt_text, answer in history:

            formatted_history.append(
                {
                    "role": "human",
                    "content": prompt_text
                }
            )

            formatted_history.append(
                {
                    "role": "ai",
                    "content": answer
                }
            )

        return {
            "history": formatted_history
        }

    finally:

        cur.close()
        conn.close()


# ============================================================
# RAG QUERY
# ============================================================

@app.post("/query")
def query_rag(req: QueryRequest):

    conn = get_db_conn()
    cur = conn.cursor()

    try:

        # ----------------------------------------------------
        # Check that user exists
        # ----------------------------------------------------

        cur.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            """,
            (req.user_id,)
        )

        user = cur.fetchone()

        if not user:
            return {
                "error": "User does not exist. Please login again."
            }

        # ----------------------------------------------------
        # Get chat history
        # ----------------------------------------------------

        cur.execute(
            """
            SELECT prompt, answer
            FROM chat_history
            WHERE user_id = %s
            ORDER BY id ASC
            """,
            (req.user_id,)
        )

        db_history = cur.fetchall()

        # ----------------------------------------------------
        # Convert history to LangChain messages
        # ----------------------------------------------------

        chat_history_messages = []

        for prompt_text, answer in db_history:

            chat_history_messages.append(
                HumanMessage(content=prompt_text)
            )

            chat_history_messages.append(
                AIMessage(content=answer)
            )

        # ----------------------------------------------------
        # Run RAG
        # ----------------------------------------------------

        response = rag_chain.invoke(
            {
                "input": req.text,
                "chat_history": chat_history_messages
            }
        )

        answer = response.get(
            "answer",
            "No answer found."
        )

        # ----------------------------------------------------
        # Save chat
        # ----------------------------------------------------

        cur.execute(
            """
            INSERT INTO chat_history
            (user_id, prompt, answer)
            VALUES (%s, %s, %s)
            """,
            (
                req.user_id,
                req.text,
                answer
            )
        )

        conn.commit()

        return {
            "answer": answer
        }

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()
        
