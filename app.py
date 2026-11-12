import uuid
import requests
import streamlit as st

st.set_page_config(
    page_title="SQL AI Agent",
    page_icon="🗄️",
    layout="wide",
)

API_URL = st.sidebar.text_input("FastAPI URL", "http://127.0.0.1:8000")
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🗄️ Database AI Agent")
st.caption("Ask questions about your MySQL database in natural language.")

with st.sidebar:
    st.subheader("Chat controls")
    if st.button("＋ New conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    st.caption("Each conversation has its own memory thread.")
    st.divider()
    st.markdown("**Example questions**")
    examples = [
        "Show me all tables in the database.",
        "Which are the top 10 orders?",
        "How many customers are there?",
        "Show the total number of orders by status.",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_question = example

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a question about your MySQL database...")
if not prompt and st.session_state.get("pending_question"):
    prompt = st.session_state.pop("pending_question")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking your database..."):
            try:
                response = requests.post(
                    f"{API_URL.rstrip('/')}/chat",
                    json={
                        "query": prompt,
                        "thread_id": st.session_state.thread_id,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                answer = response.json()["answer"]
            except requests.exceptions.ConnectionError:
                answer = "Could not connect to FastAPI. Start the API with: uvicorn api:app --reload"
            except requests.exceptions.HTTPError:
                try:
                    answer = response.json().get("detail", response.text)
                except Exception:
                    answer = response.text
            except requests.exceptions.Timeout:
                answer = "The request timed out. Try a simpler question."
            except Exception as exc:
                answer = f"Unexpected error: {exc}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
