import streamlit as st
import pandas as pd

from chatbot import ask_question
from google_pay_parser import parse_google_pay_html


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Spend Analyzer",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("💰 Spend Analyzer")

st.write(
    "Upload your Google Pay or Credit Card statement "
    "to analyze your spending using AI."
)


# =========================================================
# FILE UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "Upload your statement",
    type=[
        "html",
        "csv",
        "xlsx",
        "xls"
    ],
    help="Supported formats: Google Pay HTML, CSV and Excel"
)


# =========================================================
# NO FILE
# =========================================================

if uploaded_file is None:

    st.info(
        "👆 Upload a Google Pay HTML, CSV or Excel statement "
        "to get started."
    )

    st.stop()


# =========================================================
# READ FILE
# =========================================================

try:

    file_name = uploaded_file.name.lower()


    # -----------------------------------------------------
    # GOOGLE PAY HTML
    # -----------------------------------------------------

    if file_name.endswith(".html"):

        with st.spinner(
            "📄 Reading Google Pay statement..."
        ):

            df = parse_google_pay_html(
                uploaded_file
            )


    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

    elif file_name.endswith(".csv"):

        df = pd.read_csv(
            uploaded_file
        )


    # -----------------------------------------------------
    # EXCEL
    # -----------------------------------------------------

    elif file_name.endswith(
        (".xlsx", ".xls")
    ):

        df = pd.read_excel(
            uploaded_file
        )


    else:

        st.error(
            "Unsupported file format."
        )

        st.stop()


except Exception as e:

    st.error(
        f"Unable to read the file: {e}"
    )

    st.stop()


# =========================================================
# CHECK DATA
# =========================================================

if df.empty:

    st.warning(
        "No transactions were found in this file."
    )

    st.stop()


# =========================================================
# SUCCESS MESSAGE
# =========================================================

st.success(
    f"File uploaded successfully: "
    f"{uploaded_file.name}"
)


# =========================================================
# BASIC INFORMATION
# =========================================================

st.subheader("📊 Statement Summary")


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Transactions",
        len(df)
    )


with col2:

    st.metric(
        "Columns",
        len(df.columns)
    )


with col3:

    if "Amount" in df.columns:

        total_amount = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).sum()

        st.metric(
            "Total Amount",
            f"₹{total_amount:,.2f}"
        )

    else:

        st.metric(
            "Total Amount",
            "N/A"
        )


with col4:

    if "Transaction Type" in df.columns:

        expenses = (
            df["Transaction Type"]
            .astype(str)
            .str.lower()
            .eq("expense")
            .sum()
        )

        st.metric(
            "Expenses",
            expenses
        )

    else:

        st.metric(
            "Expenses",
            "N/A"
        )


# =========================================================
# TRANSACTIONS
# =========================================================

st.subheader("📄 Your Transactions")


# Hide sensitive/internal columns from the default view

display_columns = [
    "Transaction Date",
    "Description",
    "Merchant Name",
    "Amount",
    "Transaction Type",
    "Status",
    "Category",
    "Source",
    "Month",
    "Year"
]


available_columns = [
    col
    for col in display_columns
    if col in df.columns
]


if available_columns:

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        height=450
    )

else:

    st.dataframe(
        df,
        use_container_width=True,
        height=450
    )


# =========================================================
# CHATBOT
# =========================================================

st.divider()

st.subheader("🤖 Ask Your Spend Analyzer")


st.caption(
    "Examples: "
    "How much did I spend on fuel? | "
    "How much did I spend this month? | "
    "What are my top merchants?"
)


question = st.text_input(
    "Ask a question about your spending",
    placeholder="Example: How much did I spend on fuel?"
)


# =========================================================
# PROCESS QUESTION
# =========================================================

if question:

    try:

        with st.spinner(
            "🤖 Analyzing your spending..."
        ):

            answer, sql, result = ask_question(
                df,
                question
            )


        # -------------------------------------------------
        # ANSWER
        # -------------------------------------------------

        st.success(
            answer
        )


        # -------------------------------------------------
        # ANALYSIS DETAILS
        # -------------------------------------------------

        with st.expander(
            "🔍 Show analysis details"
        ):

            st.write(
                "Generated SQL:"
            )

            st.code(
                sql,
                language="sql"
            )


            st.write(
                "Database Result:"
            )

            if result.empty:

                st.info(
                    "No matching records found."
                )

            else:

                st.dataframe(
                    result,
                    use_container_width=True
                )


    except Exception as e:

        st.error(
            f"Unable to answer the question: {e}"
        )