import hashlib
import uuid
import requests
import streamlit as st
st.set_page_config(
    page_title="SQL AI Agent",
    page_icon="🗄️",
    layout="wide",
)
DEFAULT_API_URL = "http://127.0.0.1:8000"
API_URL = st.sidebar.text_input("FastAPI URL", DEFAULT_API_URL).rstrip("/")
if "thread_ids_by_db" not in st.session_state:
    st.session_state.thread_ids_by_db = {}
if "messages_by_db" not in st.session_state:
    st.session_state.messages_by_db = {}
if "uploaded_fingerprints" not in st.session_state:
    st.session_state.uploaded_fingerprints = set()
if "upload_widget_version" not in st.session_state:
    st.session_state.upload_widget_version = 0
def api_error_message(response):
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    return str(detail)
def fetch_databases():
    response = requests.get(f"{API_URL}/databases", timeout=15)
    response.raise_for_status()
    return [item["name"] for item in response.json().get("databases", [])]
st.title("🗄️ Database AI Agent")
st.caption("Ask questions about your selected SQLite database in natural language.")
with st.sidebar:
    st.subheader("Database management")
    st.caption("Upload SQLite database files (.db, .sqlite, .sqlite3).")
    upload_key = f"database_upload_{st.session_state.upload_widget_version}"
    uploaded_files = st.file_uploader(
        "Upload database files",
        type=["db", "sqlite", "sqlite3"],
        accept_multiple_files=True,
        key=upload_key,
    )
    if uploaded_files:
        upload_success = False
        upload_failed = False
        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.getvalue()
            fingerprint = hashlib.sha256(uploaded_file.name.encode("utf-8") + file_bytes).hexdigest()
            if fingerprint in st.session_state.uploaded_fingerprints:
                continue
            try:
                response = requests.post(
                    f"{API_URL}/databases/upload",
                    files={"file": (uploaded_file.name, file_bytes, "application/octet-stream")},
                    timeout=120,
                )
                if response.ok:
                    st.session_state.uploaded_fingerprints.add(fingerprint)
                    st.success(f"Uploaded {uploaded_file.name}")
                    upload_success = True
                else:
                    upload_failed = True
                    st.error(f"{uploaded_file.name}: {api_error_message(response)}")
            except requests.exceptions.ConnectionError:
                upload_failed = True
                st.error("Could not connect to FastAPI. Start it with: uvicorn api:app --reload")
                break
            except requests.exceptions.Timeout:
                upload_failed = True
                st.error(f"Upload timed out: {uploaded_file.name}")
                break
        if upload_success and not upload_failed:
            st.session_state.upload_widget_version += 1
            st.rerun()
    st.divider()
    st.subheader("Select database")
    try:
        database_options = fetch_databases()
        if not database_options:
            st.warning("No SQLite databases found. Upload a database to get started.")
            selected_database = None
        else:
            if "selected_database" not in st.session_state or st.session_state.selected_database not in database_options:
                st.session_state.selected_database = database_options[0]
            selected_database = st.selectbox(
                "Available databases",
                options=database_options,
                key="selected_database",
            )
            st.caption(f"{len(database_options)} database(s) available in the db folder.")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to FastAPI. Start the backend first.")
        database_options = []
        selected_database = None
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load databases: {exc}")
        database_options = []
        selected_database = None
    st.divider()
    st.subheader("Chat controls")
    if selected_database:
        if st.button("＋ New conversation", use_container_width=True):
            st.session_state.thread_ids_by_db[selected_database] = str(uuid.uuid4())
            st.session_state.messages_by_db[selected_database] = []
            st.rerun()
        st.caption("Each database has its own conversation memory and chat history.")
        st.divider()
        st.markdown("**Example questions**")
        examples = [
            "Show me all tables in the database.",
            "Which are the top 10 records?",
            "How many records are there in the main table?",
            "Show the total number of records grouped by status.",
        ]
        for example in examples:
            if st.button(example, use_container_width=True):
                st.session_state.pending_question = example
if not selected_database:
    st.info("Upload a SQLite database or place .db/.sqlite files in the project's db folder, then select one from the sidebar.")
    st.stop()
if selected_database not in st.session_state.thread_ids_by_db:
    st.session_state.thread_ids_by_db[selected_database] = str(uuid.uuid4())
if selected_database not in st.session_state.messages_by_db:
    st.session_state.messages_by_db[selected_database] = []
messages = st.session_state.messages_by_db[selected_database]
st.caption(f"Currently querying: **{selected_database}**")
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
prompt = st.chat_input(f"Ask a question about {selected_database}...")
if not prompt and st.session_state.get("pending_question"):
    prompt = st.session_state.pop("pending_question")
if prompt:
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(f"Querying {selected_database}..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "query": prompt,
                        "thread_id": st.session_state.thread_ids_by_db[selected_database],
                        "database_name": selected_database,
                    },
                    timeout=180,
                )
                response.raise_for_status()
                answer = response.json()["answer"]
            except requests.exceptions.ConnectionError:
                answer = "Could not connect to FastAPI. Start the API with: uvicorn api:app --reload"
            except requests.exceptions.HTTPError:
                answer = api_error_message(response)
            except requests.exceptions.Timeout:
                answer = "The request timed out. Try a simpler question."
            except requests.exceptions.RequestException as exc:
                answer = f"Request error: {exc}"
            except Exception as exc:
                answer = f"Unexpected error: {exc}"
        st.markdown(answer)
    messages.append({"role": "assistant", "content": answer})