import streamlit as st
import pandas as pd

from chatbot import answer_question

st.set_page_config(
    page_title="Spend Analyzer",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Spend Analyzer")
st.write("Upload your GPay or Credit Card statement to analyze your spending.")

uploaded_file = st.file_uploader(
    "Upload your statement",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file is not None:

    # Read the uploaded file
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"File uploaded successfully: {uploaded_file.name}")

    st.subheader("📄 Your Transactions")

    st.dataframe(
        df,
        use_container_width=True,
        height=400
    )

    st.subheader("📊 Basic Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Number of Transactions", len(df))

    with col2:
        st.metric("Number of Columns", len(df.columns))

    with col3:
        st.metric("File Name", uploaded_file.name)

else:
    st.info("👆 Upload a CSV or Excel statement to get started.")



st.divider()

st.subheader("🤖 Ask Your Spend Analyzer")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about your spending..."):

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Generate answer
    response = answer_question(df, prompt)

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })