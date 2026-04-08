import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd

# --- Configuration ---
st.set_page_config(page_title="SOW Order Book Report", layout="wide")
st.title("📄 SOW Order Book Report")

# --- Sidebar ---
with st.sidebar:
    api_key = st.text_input("Enter Groq API Key", type="password")

# --- Data model matching Order Book columns ---
class SOWData(BaseModel):
    entity: Optional[str] = Field(None, description="Entity - US or APAC")
    month: Optional[str] = Field(None, description="Month in which SOW is signed")
    quarter: Optional[str] = Field(None, description="Calendar quarter e.g. Q1, Q2")
    sbu: Optional[str] = Field(None, description="Strategic Business Unit based on customer master")
    bu_head: Optional[str] = Field(None, description="BU Head name based on customer master")
    group_customer: Optional[str] = Field(None, description="Group Customer name based on customer master")
    ee_en_nn: Optional[str] = Field(None, description="EE/EN/NN classification based on SOW")
    contract_start_date: Optional[str] = Field(None, description="Contract start date")
    contract_end_date: Optional[str] = Field(None, description="Contract end date")
    terms_months: Optional[int] = Field(None, description="Term of SOW in months")
    geo: Optional[str] = Field(None, description="Geography based on start date")
    skills: Optional[str] = Field(None, description="Skills required as per SOW")
    location_of_service: Optional[str] = Field(None, description="Location of service delivery")
    notes: Optional[str] = Field(None, description="All important points from SOW")
    acv: Optional[float] = Field(None, description="Annual Contract Value in USD")
    tcv: Optional[float] = Field(None, description="Total Contract Value in USD")
    target_fte_onshore: Optional[float] = Field(None, description="Target FTE headcount onshore")
    target_fte_offshore: Optional[float] = Field(None, description="Target FTE headcount offshore")
    rates: Optional[str] = Field(None, description="Billing rates as per SOW")
    monthly_rate: Optional[float] = Field(None, description="Monthly billing rate in USD")

def process_sow(uploaded_file, key):
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    loader = PyPDFLoader("temp.pdf")
    pages = loader.load_and_split()
    full_text = " ".join([p.page_content for p in pages[:5]])

    parser = PydanticOutputParser(pydantic_object=SOWData)

    prompt = PromptTemplate(
        template=(
            "You are an expert contract analyst. Extract all the following fields from this Statement of Work (SOW) document.\n"
            "For fields not explicitly mentioned, infer where possible or leave as null.\n\n"
            "{format_instructions}\n\n"
            "Document:\n{text}\n"
        ),
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=key, temperature=0)
    chain = prompt | llm | parser
    return chain.invoke({"text": full_text})

# --- UI ---
uploaded_file = st.file_uploader("Upload SOW (PDF)", type="pdf")

if uploaded_file and api_key:
    with st.spinner("Analyzing SOW document..."):
        try:
            result = process_sow(uploaded_file, api_key)
            data = result.dict()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()

    # --- Financial calculations ---
    monthly_rate = data.get("monthly_rate") or 0
    terms = data.get("terms_months") or 12
    tcv = data.get("tcv") or (monthly_rate * terms)
    acv = data.get("acv") or (monthly_rate * 12)

    # Monthly revenue spread (equal distribution)
    months = ["Jan'25","Feb'25","Mar'25","Apr'25","May'25","Jun'25",
              "Jul'25","Aug'25","Sep'25","Oct'25","Nov'25","Dec'25"]
    monthly_rev = round(monthly_rate, 2)

    # --- Section 1: Contract Info ---
    st.subheader("📋 Contract Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Entity:** {data.get('entity') or '-'}")
        st.write(f"**Group Customer:** {data.get('group_customer') or '-'}")
        st.write(f"**BU Head:** {data.get('bu_head') or '-'}")
        st.write(f"**SBU:** {data.get('sbu') or '-'}")
    with col2:
        st.write(f"**Month Signed:** {data.get('month') or '-'}")
        st.write(f"**Quarter:** {data.get('quarter') or '-'}")
        st.write(f"**EE/EN/NN:** {data.get('ee_en_nn') or '-'}")
        st.write(f"**GEO:** {data.get('geo') or '-'}")
    with col3:
        st.write(f"**Start Date:** {data.get('contract_start_date') or '-'}")
        st.write(f"**End Date:** {data.get('contract_end_date') or '-'}")
        st.write(f"**Terms (Months):** {data.get('terms_months') or '-'}")
        st.write(f"**Location of Service:** {data.get('location_of_service') or '-'}")

    st.divider()

    # --- Section 2: Financials ---
    st.subheader("💰 Financials")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("ACV", f"${acv:,.2f}")
    with col5:
        st.metric("TCV", f"${tcv:,.2f}")
    with col6:
        st.metric("Monthly Rate", f"${monthly_rate:,.2f}")

    st.divider()

    # --- Section 3: Resources & Skills ---
    st.subheader("🛠 Resources & Skills")
    col7, col8 = st.columns(2)
    with col7:
        st.write(f"**Target FTE Onshore:** {data.get('target_fte_onshore') or '-'}")
        st.write(f"**Target FTE Offshore:** {data.get('target_fte_offshore') or '-'}")
        st.write(f"**Rates:** {data.get('rates') or '-'}")
    with col8:
        st.info(f"**Skills:** {data.get('skills') or 'Not specified'}")

    st.divider()

    # --- Section 4: Monthly Revenue Table ---
    st.subheader("📅 CY'25 Monthly Revenue Spread")
    rev_data = {m: monthly_rev for m in months}
    rev_data["Q1"] = round(monthly_rev * 3, 2)
    rev_data["Q2"] = round(monthly_rev * 3, 2)
    rev_data["Q3"] = round(monthly_rev * 3, 2)
    rev_data["Q4"] = round(monthly_rev * 3, 2)
    rev_df = pd.DataFrame([rev_data])
    st.dataframe(rev_df, use_container_width=True)

    st.divider()

    # --- Section 5: Notes ---
    st.subheader("📝 Notes & Ambiguities")
    st.write(data.get("notes") or "No notes extracted.")

    # --- Export ---
    st.divider()
    export_df = pd.DataFrame([{
        "Entity": data.get("entity"),
        "Month": data.get("month"),
        "Quarter": data.get("quarter"),
        "SBU": data.get("sbu"),
        "BU Head": data.get("bu_head"),
        "Group Customer": data.get("group_customer"),
        "EE/EN/NN": data.get("ee_en_nn"),
        "Contract Start Date": data.get("contract_start_date"),
        "Contract End Date": data.get("contract_end_date"),
        "Terms (Months)": data.get("terms_months"),
        "GEO": data.get("geo"),
        "Skills": data.get("skills"),
        "Location of Service": data.get("location_of_service"),
        "Notes": data.get("notes"),
        "ACV": acv,
        "TCV": tcv,
        "Target FTE Onshore": data.get("target_fte_onshore"),
        "Target FTE Offshore": data.get("target_fte_offshore"),
        "Rates": data.get("rates"),
        **{m: monthly_rev for m in months},
        "Q1": round(monthly_rev * 3, 2),
        "Q2": round(monthly_rev * 3, 2),
        "Q3": round(monthly_rev * 3, 2),
        "Q4": round(monthly_rev * 3, 2),
    }])
    st.download_button(
        label="⬇️ Download as Excel",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="sow_order_book.csv",
        mime="text/csv"
    )

elif not api_key:
    st.info("Please enter your Groq API key in the sidebar to begin.")
