import pandas as pd


def answer_question(df, question):
    question = question.lower().strip()

    # Make sure Amount is numeric
    df = df.copy()
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df = df.dropna(subset=["Amount"])

    # Total spending = debit transactions
    if "total" in question and "spend" in question:
        spending = df[df["Transaction Type"].str.lower() == "debit"]

        total = spending["Amount"].sum()

        return f"Your total spending is ₹{total:,.2f}."

    # Number of transactions
    if "number of transaction" in question or "how many transaction" in question:
        return f"You have {len(df):,} transactions."

    # Top categories
    if "top" in question and "categor" in question:
        spending = df[df["Transaction Type"].str.lower() == "debit"]

        result = (
            spending.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )

        response = "Your top 5 spending categories are:\n\n"

        for category, amount in result.items():
            response += f"- **{category}** — ₹{amount:,.2f}\n"

        return response

    # Spending by category
    if "grocery" in question:
        spending = df[
            (df["Transaction Type"].str.lower() == "debit")
            & (df["Category"].str.lower() == "grocery")
        ]

        total = spending["Amount"].sum()

        return f"You spent ₹{total:,.2f} on groceries."

    return (
        "I understand that you are asking about your spending, "
        "but I don't know how to answer that question yet."
    )