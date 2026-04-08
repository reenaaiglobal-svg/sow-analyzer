import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
import os

# --- Configuration ---
st.set_page_config(page_title="SOW Intelligence Report", layout="wide")
st.title("📄 SOW Extraction & Analysis Report")

# --- Sidebar for API Key ---
with st.sidebar:
    api_key = st.text_input("Enter Google Gemini API Key", type="password")

# --- Pydantic model for structured extraction ---
class SOWData(BaseModel):
    client_name: Optional[str] = Field(None, description="Name of the client")
    vendor_name: Optional[str] = Field(None, description="Name of the vendor")
    start_date: Optional[str] = Field(None, description="Contract start date")
    end_date: Optional[str] = Field(None, description="Contract end date")
    total_resources: Optional[int] = Field(None, description="Total number of resources")
    monthly_rate: Optional[float] = Field(None, description="Monthly rate in dollars")
    skills_required: Optional[str] = Field(None, description="Skills required")
    is_signed: Optional[bool] = Field(None, description="Whether the contract is signed")
    ambiguities: Optional[str] = Field(None, description="Any ambiguities or risks found")

def process_sow(uploaded_file, key):
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    loader = PyPDFLoader("temp.pdf")
    pages = loader.load_and_split()
    full_text = " ".join([p.page_content for p in pages[:5]])

    parser = PydanticOutputParser(pydantic_object=SOWData)

    prompt = PromptTemplate(
        template="Extract the following information from this Statement of Work document:\n{format_instructions}\n\nDocument:\n{text}\n",
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=key, temperature=0)
    chain = prompt | llm | parser

    return chain.invoke({"text": full_text})

# --- UI Layout ---
uploaded_file = st.file_uploader("Upload SOW (PDF)", type="pdf")

if uploaded_file and api_key:
    with st.spinner("Analyzing document..."):
        result = process_sow(uploaded_file, api_key)
        if not result:
            st.error("Could not extract data. Please check the PDF and try again.")
            st.stop()
        data = result.dict()

        rate = data.get("monthly_rate") or 0
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
            st.info(data.get("skills_required") or "Not specified")
            st.write(f"**Resource Count:** {data.get('total_resources')}")

        with col4:
            st.subheader("⚖️ Compliance & Risk")
            status = "✅ Signed" if data.get("is_signed") else "❌ Unsigned"
            st.write(f"**Status:** {status}")
            st.warning(f"**Ambiguities:** {data.get('ambiguities') or 'None detected'}")

elif not api_key:
    st.info("Please enter your Gemini API key in the sidebar to begin.")
