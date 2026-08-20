import os
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# RAG Imports
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")

if not DB_URL:
    raise ValueError("DATABASE_URL is not set in .env")



os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_conn():
    return psycopg2.connect(DB_URL)


# ============================================================
# RAG SETUP
# ============================================================

FAISS_PATH = "../faiss_index/"

print("Loading embeddings...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

print("Loading FAISS index...")

db = FAISS.load_local(
    FAISS_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

print("Loading Gemini...")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0.7
)

retriever = db.as_retriever(
    search_kwargs={"k": 3}
)


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

print("RAG chain created.")


# ============================================================
# FASTAPI APP
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
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def read_root():
    return {
        "message": "Welcome to FastAPI. Go to /docs to get started."
    }


# ============================================================
# LOGIN / SIGNUP
# ============================================================

@app.post("/get_or_create_user")
def get_or_create_user(req: UserRequest):

    conn = get_db_conn()
    cur = conn.cursor()

    try:

        # ----------------------------------------------------
        # 1. Check if username already exists
        # ----------------------------------------------------

        cur.execute(
            """
            SELECT id, username, email
            FROM users
            WHERE username = %s
            """,
            (req.username,)
        )

        user_row = cur.fetchone()

        # ----------------------------------------------------
        # 2. Existing user
        # ----------------------------------------------------

        if user_row:

            user_id = user_row[0]

            return {
                "user_id": user_id,
                "username": user_row[1],
                "email": user_row[2]
            }

        # ----------------------------------------------------
        # 3. Create new user
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Format history for frontend
        # ----------------------------------------------------

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
        # 1. Get previous conversation history
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
        # 2. Convert database history into LangChain messages
        # ----------------------------------------------------

        chat_history_messages = []

        for prompt_text, answer in db_history:

            chat_history_messages.append(
                HumanMessage(
                    content=prompt_text
                )
            )

            chat_history_messages.append(
                AIMessage(
                    content=answer
                )
            )

        # ----------------------------------------------------
        # 3. Run RAG
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
        # 4. Save Q&A into PostgreSQL
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

        # ----------------------------------------------------
        # 5. Return answer
        # ----------------------------------------------------

        return {
            "answer": answer
        }

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()