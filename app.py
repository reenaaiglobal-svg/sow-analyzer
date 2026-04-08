import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain.chains import create_extraction_chain
import os

# --- Configuration & Styles ---
st.set_page_config(page_title="SOW Intelligence Report", layout="wide")
st.title("📄 SOW Extraction & Analysis Report")

# --- Sidebar for API Keys ---
with st.sidebar:
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    os.environ["OPENAI_API_KEY"] = api_key

# --- Structured Schema for Extraction ---
schema = {
    "properties": {
        "client_name": {"type": "string"},
        "vendor_name": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "total_resources": {"type": "integer"},
        "monthly_rate": {"type": "number"},
        "skills_required": {"type": "string"},
        "is_signed": {"type": "boolean"},
        "ambiguities": {"type": "string"},
    },
    "required": ["client_name", "vendor_name", "monthly_rate"],
}

def process_sow(uploaded_file):
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    loader = PyPDFLoader("temp.pdf")
    pages = loader.load_and_split()
    full_text = " ".join([p.page_content for p in pages[:5]])

    llm = ChatOpenAI(temperature=0, model="gpt-4")
    chain = create_extraction_chain(schema, llm)
    
    return chain.invoke(full_text)

# --- UI Layout ---
uploaded_file = st.file_uploader("Upload SOW (PDF)", type="pdf")

if uploaded_file and api_key:
    with st.spinner("Analyzing document..."):
        results = process_sow(uploaded_file)
        if not results:
            st.error("Could not extract data from the document. Please check the PDF and try again.")
            st.stop()
        data = results[0]
        
        rate = data.get("monthly_rate", 0)
        tcv = rate * 12
        acv = tcv

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Contract Info")
            st.write(f"**Client:** {data.get('client_name')}")
            st.write(f"**Vendor:** {data.get('vendor_name')}")
            st.write(f"**Timeline:** {data.get('start_date')} to {data.get('end_date')}")

        with col2:
            st.subheader("💰 Financials")
            st.metric("Monthly Cost", f"${rate:,.2f}")
            st.metric("Estimated TCV", f"${tcv:,.2f}")
            st.metric("Estimated ACV", f"${acv:,.2f}")

        st.divider()

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("🛠 Skills & Resources")
            st.info(data.get("skills_required", "Not specified"))
            st.write(f"**Resource Count:** {data.get('total_resources')}")

        with col4:
            st.subheader("⚖️ Compliance & Risk")
            status = "✅ Signed" if data.get("is_signed") else "❌ Unsigned"
            st.write(f"**Status:** {status}")
            st.warning(f"**Ambiguities:** {data.get('ambiguities', 'None detected')}")

elif not api_key:
    st.info("Please enter your API key in the sidebar to begin.")
