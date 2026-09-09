import re

import duckdb
import ollama


# =========================================================
# OLLAMA MODEL
# =========================================================

MODEL = "llama3.2"


# =========================================================
# GET DATABASE SCHEMA
# =========================================================

def get_schema(df):

    schema = []

    for col, dtype in zip(
        df.columns,
        df.dtypes
    ):

        safe_col = col.replace(
            '"',
            '""'
        )

        schema.append(
            f'"{safe_col}" ({dtype})'
        )


    return "\n".join(
        schema
    )


# =========================================================
# GENERATE SQL
# =========================================================

def generate_sql(
    question,
    df
):

    schema = get_schema(
        df
    )


    prompt = f"""
You are an expert financial data analyst.

You write DuckDB SQL for a personal spending analysis application.

The transaction data is stored in:

transactions

DATABASE SCHEMA:
{schema}

USER QUESTION:
{question}


=========================================================
GENERAL RULES
=========================================================

1. Generate exactly ONE SQL SELECT query.

2. Use ONLY the table:

transactions

3. Use ONLY columns present in the schema.

4. Never invent columns.

5. Always put column names inside double quotes.

Example:

"Transaction Date"
"Merchant Name"
"Transaction Type"
"Amount"
"Category"

6. Never modify the database.

7. Never use:

INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE
MERGE
REPLACE

8. Return ONLY SQL.

9. Do not use markdown.

10. Do not use ```sql.

11. Do not provide explanations.


=========================================================
SPENDING RULE
=========================================================

When the user asks about:

spending
spent
expenses
expense
purchase
purchases
cost
how much paid

assume they mean successful expenses.

Therefore normally include:

"Transaction Type" = 'Expense'

AND

"Status" = 'Completed'


Example:

SELECT SUM("Amount") AS total_spent
FROM transactions
WHERE "Transaction Type" = 'Expense'
AND "Status" = 'Completed';


=========================================================
AMOUNT RULE
=========================================================

When the user asks:

"How much did I spend?"

use:

SUM("Amount")


=========================================================
TRANSACTION COUNT
=========================================================

When the user asks:

"How many transactions?"

use:

COUNT(*)


=========================================================
MERCHANT / DESCRIPTION SEARCH
=========================================================

If the user mentions something such as:

fuel
petrol
Amazon
Flipkart
D-Mart
groceries
vegetables
hotel
restaurant
medical
pharmacy

search relevant text fields.

Use:

"Merchant Name"
"Description"
"Category"


For example, fuel:

WHERE
(
    "Merchant Name" ILIKE '%fuel%'
    OR "Merchant Name" ILIKE '%petrol%'
    OR "Merchant Name" ILIKE '%hpcl%'
    OR "Merchant Name" ILIKE '%bpcl%'
    OR "Merchant Name" ILIKE '%indian oil%'
    OR "Category" ILIKE '%fuel%'
    OR "Description" ILIKE '%fuel%'
    OR "Description" ILIKE '%petrol%'
)


=========================================================
CATEGORY QUESTIONS
=========================================================

If the user asks about categories:

GROUP BY "Category"


Example:

SELECT
    "Category",
    SUM("Amount") AS total_spent
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
GROUP BY "Category"
ORDER BY total_spent DESC
LIMIT 10;


=========================================================
TOP MERCHANTS
=========================================================

If the user asks:

top merchants
where do I spend most
biggest merchants

use:

GROUP BY "Merchant Name"

and:

SUM("Amount")

ORDER BY total_spent DESC


=========================================================
HIGHEST TRANSACTION
=========================================================

If the user asks:

highest expense
largest transaction
biggest purchase

use:

ORDER BY "Amount" DESC

and:

LIMIT 1


=========================================================
MONTHLY SPENDING
=========================================================

If the user asks:

monthly spending
spending by month
how much did I spend each month

use:

"Month"

GROUP BY "Month"


Example:

SELECT
    "Month",
    SUM("Amount") AS total_spent
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
GROUP BY "Month"
ORDER BY "Month";


=========================================================
YEARLY SPENDING
=========================================================

If the user asks:

yearly spending
spending by year

use:

"Year"

GROUP BY "Year"


=========================================================
DATE QUESTIONS
=========================================================

For date filtering use:

"Transaction Date"


For example:

WHERE "Transaction Date"
BETWEEN '2026-01-01'
AND '2026-01-31'


=========================================================
INCOME QUESTIONS
=========================================================

If the user asks:

income
money received
received money

use:

"Transaction Type" = 'Income'


Do NOT use Expense.


=========================================================
REQUEST QUESTIONS
=========================================================

If the user specifically asks about requests:

use:

"Transaction Type" = 'Request'


=========================================================
PENDING / FAILED
=========================================================

For normal spending questions:

DO NOT include:

Pending

or:

Failed


Only completed transactions should normally count.


=========================================================
TEXT SEARCH
=========================================================

For text matching use:

ILIKE


Example:

"Merchant Name" ILIKE '%amazon%'


=========================================================
IMPORTANT
=========================================================

The database may contain thousands of transactions.

Do the calculation using SQL.

Do not ask the LLM to calculate the total manually.


=========================================================
EXAMPLES
=========================================================


QUESTION:

How much did I spend on fuel?


SQL:

SELECT SUM("Amount") AS total_spent
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
    AND (
        "Merchant Name" ILIKE '%fuel%'
        OR "Merchant Name" ILIKE '%petrol%'
        OR "Merchant Name" ILIKE '%hpcl%'
        OR "Merchant Name" ILIKE '%bpcl%'
        OR "Merchant Name" ILIKE '%indian oil%'
        OR "Category" ILIKE '%fuel%'
        OR "Description" ILIKE '%fuel%'
        OR "Description" ILIKE '%petrol%'
    );


QUESTION:

How many transactions do I have?


SQL:

SELECT COUNT(*) AS transaction_count
FROM transactions;


QUESTION:

What are my top spending categories?


SQL:

SELECT
    "Category",
    SUM("Amount") AS total_spent
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
GROUP BY "Category"
ORDER BY total_spent DESC
LIMIT 10;


QUESTION:

What are my top 5 merchants?


SQL:

SELECT
    "Merchant Name",
    SUM("Amount") AS total_spent
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
    AND "Merchant Name" IS NOT NULL
    AND "Merchant Name" <> ''
GROUP BY "Merchant Name"
ORDER BY total_spent DESC
LIMIT 5;


QUESTION:

What was my highest expense?


SQL:

SELECT
    "Transaction Date",
    "Merchant Name",
    "Amount"
FROM transactions
WHERE
    "Transaction Type" = 'Expense'
    AND "Status" = 'Completed'
ORDER BY "Amount" DESC
LIMIT 1;


Now generate the SQL.

SQL:
"""


    # =====================================================
    # CALL OLLAMA
    # =====================================================

    response = ollama.chat(

        model=MODEL,

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )


    sql = response[
        "message"
    ][
        "content"
    ].strip()


    # =====================================================
    # CLEAN SQL
    # =====================================================

    sql = sql.replace(
        "```sql",
        ""
    )

    sql = sql.replace(
        "```",
        ""
    )

    sql = sql.strip()


    # Remove accidental SQL label

    if sql.lower().startswith(
        "sql:"
    ):

        sql = sql[4:].strip()


    return sql


# =========================================================
# VALIDATE SQL
# =========================================================

def validate_sql(sql):

    sql_clean = sql.strip()

    sql_lower = sql_clean.lower()


    # -----------------------------------------------------
    # MUST START WITH SELECT
    # -----------------------------------------------------

    if not sql_lower.startswith(
        "select"
    ):

        raise ValueError(
            "Only SELECT queries are allowed."
        )


    # -----------------------------------------------------
    # NO MULTIPLE STATEMENTS
    # -----------------------------------------------------

    if ";" in sql_clean:

        raise ValueError(
            "Multiple SQL statements are not allowed."
        )


    # -----------------------------------------------------
    # FORBIDDEN COMMANDS
    # -----------------------------------------------------

    forbidden = [

        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "create ",
        "truncate ",
        "replace ",
        "merge "

    ]


    for word in forbidden:

        if word in sql_lower:

            raise ValueError(
                "Unsafe SQL detected."
            )


# =========================================================
# RUN SQL
# =========================================================

def run_sql(
    df,
    sql
):

    # -----------------------------------------------------
    # VALIDATE
    # -----------------------------------------------------

    validate_sql(
        sql
    )


    # -----------------------------------------------------
    # CONNECT DUCKDB
    # -----------------------------------------------------

    con = duckdb.connect()


    try:

        # Register dataframe

        con.register(
            "transactions",
            df
        )


        # Execute

        result = con.execute(
            sql
        ).df()


    finally:

        con.close()


    return result


# =========================================================
# GENERATE NATURAL LANGUAGE ANSWER
# =========================================================

def generate_answer(
    question,
    sql,
    result
):

    # -----------------------------------------------------
    # EMPTY RESULT
    # -----------------------------------------------------

    if result.empty:

        return (
            "I couldn't find any transactions "
            "matching your question."
        )


    # -----------------------------------------------------
    # RESULT TO TEXT
    # -----------------------------------------------------

    result_text = result.to_string(
        index=False
    )


    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are a personal spending assistant.

USER QUESTION:
{question}

DATABASE RESULT:
{result_text}


Answer the user's question using ONLY the database result.


RULES:

1. Never invent numbers.

2. Never invent transactions.

3. Do not calculate values that are not present
   in the database result.

4. Be concise.

5. Use Indian Rupee symbol ₹ where appropriate.

6. Format amounts with commas.

7. Do not mention SQL.

8. Do not mention DuckDB.

9. Do not mention the database.

10. Do not say you are an AI.

11. Answer directly.


Example:

Database result:

total_spent
12500


Answer:

You spent ₹12,500.


Now answer the user.
"""


    # =====================================================
    # CALL OLLAMA
    # =====================================================

    response = ollama.chat(

        model=MODEL,

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )


    return response[
        "message"
    ][
        "content"
    ].strip()


# =========================================================
# MAIN CHATBOT
# =========================================================

def ask_question(
    df,
    question
):

    # -----------------------------------------------------
    # STEP 1
    # Generate SQL
    # -----------------------------------------------------

    sql = generate_sql(
        question,
        df
    )


    # -----------------------------------------------------
    # STEP 2
    # Execute SQL
    # -----------------------------------------------------

    result = run_sql(
        df,
        sql
    )


    # -----------------------------------------------------
    # STEP 3
    # Generate Answer
    # -----------------------------------------------------

    answer = generate_answer(
        question,
        sql,
        result
    )


    return (
        answer,
        sql,
        result
    )