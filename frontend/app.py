import streamlit as st
import requests

API_URL = "https://rag-document-chatbot-hecj.onrender.com"

st.set_page_config(
    page_title="Document Chatbot",
    page_icon="🤖"
)

st.title("📚 DOCUMENT CHATBOT")
st.write(
    "Ask questions about your documents like "
    "`webscraping.txt` and `opps_java.pdf`."
)

# ============================================================
# SESSION STATE
# ============================================================

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# LOGIN / SIGNUP
# ============================================================

if st.session_state.user_id is None:

    st.subheader("Welcome! Please login or signup.")

    username = st.text_input(
        "Enter your username:",
        key="login_username"
    )

    email = st.text_input(
        "Enter your email:",
        key="login_email"
    )

    if st.button("Login / Signup", key="login_button"):

        if username and email:

            try:

                res = requests.post(
                    f"{API_URL}/get_or_create_user",
                    json={
                        "username": username,
                        "email": email
                    },
                    timeout=60
                )

                res.raise_for_status()

                data = res.json()

                st.session_state.user_id = data["user_id"]
                st.session_state.username = data["username"]

                # Load previous chat history
                res_hist = requests.post(
                    f"{API_URL}/get_history",
                    json={
                        "user_id": data["user_id"]
                    },
                    timeout=60
                )

                res_hist.raise_for_status()

                st.session_state.messages = (
                    res_hist.json()["history"]
                )

                st.rerun()

            except Exception as e:

                st.error(f"Error: {e}")

        else:

            st.warning(
                "Please enter username and email."
            )


# ============================================================
# CHAT INTERFACE
# ============================================================

else:

    st.sidebar.header(
        f"Logged in as: {st.session_state.username}"
    )

    if st.sidebar.button("Logout"):

        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.messages = []

        st.rerun()

    st.header("💬 Chat Interface")

    st.write(
        "Ask me anything about your documents."
    )

    # Display previous messages
    for chat in st.session_state.messages:

        role = chat["role"]

        # Streamlit accepts human/ai in your current history,
        # but assistant/user are safer standard roles.
        display_role = (
            "user"
            if role == "human"
            else "assistant"
        )

        with st.chat_message(display_role):
            st.markdown(chat["content"])


    # ========================================================
    # NEW QUESTION
    # ========================================================

    if prompt := st.chat_input(
        "Ask me anything..."
    ):

        # Show user question
        st.session_state.messages.append(
            {
                "role": "human",
                "content": prompt
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)


        # Ask backend
        with st.chat_message("assistant"):

            with st.spinner(
                "Thinking... This may take a few seconds."
            ):

                try:

                    res = requests.post(
                        f"{API_URL}/query",
                        json={
                            "user_id": st.session_state.user_id,
                            "text": prompt
                        },
                        timeout=120
                    )

                    res.raise_for_status()

                    answer = res.json()["answer"]

                    st.session_state.messages.append(
                        {
                            "role": "ai",
                            "content": answer
                        }
                    )

                    st.markdown(answer)

                except requests.exceptions.Timeout:

                    st.error(
                        "The backend took too long to respond. "
                        "Please try again."
                    )

                except requests.exceptions.RequestException as e:

                    st.error(
                        f"Backend error: {e}"
                    )

                except Exception as e:

                    st.error(
                        f"Error: {e}"
                    )