import re
import duckdb
import ollama
import streamlit as st

from google import genai


LOCAL_MODEL = "llama3.2"
CLOUD_MODEL = "gemini-2.5-flash"


def get_gemini_client():
    """Return Gemini client if API key is configured."""

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        if not api_key:
            return None

        return genai.Client(api_key=api_key)

    except Exception:
        return None


def use_cloud_llm():
    """Check whether Gemini should be used."""

    return get_gemini_client() is not None


def call_llm(prompt):
    """
    Send prompt to Gemini when deployed with an API key.
    Otherwise use local Ollama.
    """

    gemini_client = get_gemini_client()

    # CLOUD MODE
    if gemini_client:

        response = gemini_client.models.generate_content(
            model=CLOUD_MODEL,
            contents=prompt
        )

        return response.text.strip()

    # LOCAL MODE
    response = ollama.chat(
        model=LOCAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"].strip()


def get_schema(df):

    schema = []

    for col, dtype in zip(df.columns, df.dtypes):
        schema.append(f'"{col}" ({dtype})')

    return "\n".join(schema)


def generate_sql(question, df):

    schema = get_schema(df)

    prompt = f"""
You are a financial data analyst.

You are given a transaction dataset.

DATABASE TABLE:
transactions

SCHEMA:
{schema}

USER QUESTION:
{question}

Your task is to generate ONE DuckDB SQL SELECT query.

STRICT RULES:

1. Return ONLY SQL.
2. The query must start with SELECT.
3. Use only the table transactions.
4. Use only columns present in the schema.
5. Always use double quotes around column names.
6. Do not use INSERT.
7. Do not use UPDATE.
8. Do not use DELETE.
9. Do not use DROP.
10. Do not use ALTER.
11. Do not use CREATE.
12. Do not use TRUNCATE.
13. Do not use MERGE.
14. Do not use REPLACE.
15. Do not use multiple SQL statements.
16. Do not include markdown.
17. Do not include ```sql.
18. Do not add explanations.

SPENDING RULES:

For spending/expense questions normally use:

"Transaction Type" = 'Expense'

and:

"Status" = 'Completed'

unless the question clearly asks for another transaction type or status.

For spending amount questions use:

SUM("Amount")

For transaction counts use:

COUNT(*)

For merchant searches use:

ILIKE.

For example:

LOWER("Merchant Name") LIKE '%amazon%'

For fuel questions consider:

fuel
petrol
diesel
hpcl
bpcl
indian oil
bharat petroleum
shell

For grocery questions consider:

grocery
groceries
supermarket
dmart
d-mart

For restaurant questions consider:

restaurant
hotel
food
cafe
swiggy
zomato

For monthly spending questions group using:

"Month"

For yearly spending questions group using:

"Year"

For top merchants:

GROUP BY "Merchant Name"
ORDER BY SUM("Amount") DESC

For highest expense:

ORDER BY "Amount" DESC

For date questions use:

"Transaction Date"

Perform calculations inside SQL.

Return only the SQL query.
"""

    sql = call_llm(prompt)

    sql = sql.strip()

    # Remove accidental markdown
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)

    return sql.strip()


def validate_sql(sql):

    sql_clean = sql.strip()

    if not sql_clean.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in sql_clean:
        raise ValueError("Multiple SQL statements are not allowed.")

    dangerous_keywords = [
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "create ",
        "truncate ",
        "merge ",
        "replace "
    ]

    sql_lower = sql_clean.lower()

    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            raise ValueError("Unsafe SQL detected.")

    return True


def run_sql(df, sql):

    validate_sql(sql)

    con = duckdb.connect()

    try:

        con.register("transactions", df)

        result = con.execute(sql).df()

        return result

    finally:

        con.close()


def generate_answer(question, sql, result):

    result_text = result.to_string(index=False)

    prompt = f"""
You are a personal financial spending assistant.

USER QUESTION:
{question}

QUERY RESULT:
{result_text}

Give a concise and easy-to-understand answer.

Rules:

1. Answer the user's question directly.
2. Do not mention SQL.
3. Do not mention DuckDB.
4. Do not mention databases.
5. Do not explain how the query was generated.
6. Use Indian Rupee formatting where appropriate.
7. If there are multiple rows, summarize the important information.
8. If the result is empty, clearly say that no matching transactions were found.
9. Do not invent numbers.
10. Use only information present in the query result.
"""

    return call_llm(prompt)


def ask_question(df, question):

    sql = generate_sql(question, df)

    result = run_sql(df, sql)

    answer = generate_answer(
        question,
        sql,
        result
    )

    return answer, sql, result