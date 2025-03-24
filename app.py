import openai
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import streamlit as st


# Function to call Azure OpenAI
def call_azure_openai(system_prompt, user_query):
    try:
        azure_openai_client = openai.AzureOpenAI(
            azure_endpoint=st.session_state.azure_openai_endpoint,
            api_key=st.session_state.azure_openai_api_key,
            api_version=st.session_state.azure_openai_api_version
        )
        
        response = azure_openai_client.chat.completions.create(
            model="gpt-4o",  # Replace with your deployment model name
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {e}"
    

def generate_embeddings(texts):
    try:
        azure_openai_client = openai.AzureOpenAI(
            azure_endpoint=st.session_state.azure_openai_endpoint,
            api_key=st.session_state.azure_openai_api_key,
            api_version=st.session_state.azure_openai_api_version
        )

        model = "text-embedding-ada-002"
         
        response = azure_openai_client.embeddings.create(input=texts, model=model).data
        return [item.embedding for item in response]
    except Exception as e:
        st.error(f"Error generating embeddings: {e}")
        return []


def query_search(query_text, top_k=5):
    try:
        query_embedding = generate_embeddings([query_text])[0]
        results = query_client.search(search_text=query_text, vector_queries=[
            VectorizedQuery(vector=query_embedding, k_nearest_neighbors=5, fields="query_vector")
        ], top=top_k)
        return [
            {"query_desc": result["query_desc"], "sql_query": result["sql_query"]}
            for result in results
        ]
    except Exception as e:
        st.error(f"Error performing query search: {e}")
        return []

def schema_search(query_text, top_k=5):
    try:
        query_embedding = generate_embeddings([query_text])[0]
        results = schema_client.search(search_text=query_text, vector_queries=[
            VectorizedQuery(vector=query_embedding, k_nearest_neighbors=5, fields="schema_vector")
        ], top=top_k)
        return [
            {
                "table_name": result["table_name"],
                "columns": result["columns"],
                "tags": result.get("tags", []),
                "synonyms": result.get("synonyms", []),
                "score": result["@search.score"]
            }
            for result in results
        ]
    except Exception as e:
        st.error(f"Error performing schema search: {e}")
        return []


# Streamlit UI setup
st.set_page_config(page_title="AI SQL Assistant", layout="wide")
st.markdown("""
    <style>
        .chat-container { max-width: 800px; margin: auto; }
        .user-message { background-color: #DCF8C6; padding: 10px; border-radius: 10px; }
        .ai-message { background-color: #EAEAEA; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# Title Bar with Logo
st.title("💬 AI SQL Query Assistant")
st.subheader("Ask me anything about your database")


# Initialize session state variables only if not already set
# Initialize session state variables if not already set

st.session_state.setdefault("azure_aisearch_endpoint", "")
st.session_state.setdefault("azure_aisearch_api_key", "")
st.session_state.setdefault("azure_aisearch_name", "")
st.session_state.setdefault("azure_openai_api_key", "")
st.session_state.setdefault("azure_openai_endpoint", "")
st.session_state.setdefault("azure_openai_api_version", "2025-01-01-preview")

st.session_state.setdefault("query_client", None)
st.session_state.setdefault("schema_client", None)
st.session_state.setdefault("connection_status", "Not Connected")

# Initialize session state for history
if "history" not in st.session_state:
    st.session_state.history = []


def get_search_clients():
    try:
        if ((st.session_state.azure_aisearch_endpoint and st.session_state.azure_aisearch_endpoint != "") 
            and (st.session_state.azure_aisearch_api_key and st.session_state.azure_aisearch_api_key != "")):

            # Initialize the Azure AI Search Clients with credentials
            credential = AzureKeyCredential(st.session_state.azure_aisearch_api_key)

            query_index_name = "aibi_query_index_dev"  # Define query index
            schema_index_name = "aibi_schema_index_dev"  # Define schema index

            query_client = SearchClient(endpoint=st.session_state.azure_aisearch_endpoint, index_name=query_index_name, credential=credential)
            schema_client = SearchClient(endpoint=st.session_state.azure_aisearch_endpoint, index_name=schema_index_name, credential=credential)

            return query_client, schema_client
        else:
            st.error("Please provide valid Azure AI Search credentials and endpoint.")
            return None, None
    except Exception as e:
        st.error(f"⚠️ Error initializing search clients: {e}")
        return None, None

# Retrieve Azure AI Search Clients
query_client, schema_client = get_search_clients()

# Sidebar with history
# Sidebar with history
with st.sidebar:
    st.header("🔍 Search History")
    if st.session_state.get("history"):
        for entry in reversed(st.session_state.history):  # Show latest first
            st.text(entry)
    else:
        st.write("No history yet.")

    # **Azure OpenAI Credentials**
    st.header("🧠 Azure OpenAI Settings")
    openai_api_key_input = st.text_input("🔑 Azure OpenAI API Key", type="password", value=st.session_state.get("azure_openai_api_key", ""))
    openai_endpoint_input = st.text_input("🌐 Azure OpenAI Endpoint", value=st.session_state.get("azure_openai_endpoint", ""))

    # **Azure AI Search Credentials**
    st.header("📊 Azure AI Search Settings")
    ai_search_key_input = st.text_input("🔑 Admin AI Search API Key", type="password", value=st.session_state.get("azure_aisearch_api_key", ""))
    ai_search_name_input = st.text_input("🌐 Azure AI Search Resource Name", value=st.session_state.get("azure_aisearch_name", ""))

    # **Connect Button**
    if st.button("🔗 Connect to Azure Resources (OpenAI & AI Search)"):
        # Update session state only when user clicks Connect
        st.session_state.azure_openai_api_key = openai_api_key_input
        st.session_state.azure_openai_endpoint = openai_endpoint_input
        st.session_state.azure_aisearch_api_key = ai_search_key_input
        st.session_state.azure_aisearch_name = ai_search_name_input

        # Construct AI Search endpoint
        if st.session_state.azure_aisearch_name:
            st.session_state.azure_aisearch_endpoint = f"https://{st.session_state.azure_aisearch_name}.search.windows.net"
        else:
            st.session_state.azure_aisearch_endpoint = ""

        # Initialize Azure AI Search clients
        get_search_clients()

        # Show success message
        st.success("✅ Connected to Azure Resources!")


# Streamlit UI
st.title("SQL Query Generator")
query = st.text_input("Enter your search query:")
col1, col2 = st.columns([1, 1])

def submit_query():
    """Handles query submission and updates history immediately"""
    if query and query not in st.session_state.history:
        st.session_state.history.append(query)  # Append before re-render

if col1.button("🔎 Submit", on_click=submit_query):

    if query:

        st.subheader("🔍 Searching for results...")
        search_placeholder = st.empty()  # Placeholder for updating results dynamically

        with st.spinner("🔎 Searching database..."):
            query_details = query_search(query)
            schema_details = schema_search(query)

        search_placeholder.empty()  # Clear the "Searching..." text

        if query_details and schema_details:
            st.subheader("📊 Search Results")
            st.write("### 🟢 Queries Found")
            for q in query_details:
                st.write(f"**📌 Query Description:** {q['query_desc']}")
                st.write(f"📝 **SQL Query:** {q['sql_query']}")

            st.write("### 🏗 Table Schema")
            for s in schema_details:
                st.write(f"**📂 Table:** {s['table_name']}")
                st.write(f"🛠 **Columns:** {s['columns']}")
                st.write(f"🏷 **Tags:** {', '.join(s['tags'])}")
                st.write(f"🔁 **Synonyms:** {', '.join(s['synonyms'])}")

            system_prompt = f"""
            You are an expert SQL query generator. Generate an accurate SQL query strictly based on predefined queries and schema.
            
            Predefined Queries:
            {query_details}
            
            Table Schema:
            {schema_details}
            """

            st.subheader("🤖 Generating AI-Powered SQL Query...")
            with st.spinner("⚡ AI is processing your query..."):
                ai_generated_query = call_azure_openai(system_prompt, query)

            st.success("✅ Query Generated Successfully!")
            st.subheader("📝 AI-Generated SQL Query")
            st.code(ai_generated_query, language="sql")
        else:
            st.warning("⚠️ No relevant results found.")
    else:
        st.warning("⚠️ Please enter a query.")

if col2.button("🔄 Reset"):
    st.session_state.history = []
    
