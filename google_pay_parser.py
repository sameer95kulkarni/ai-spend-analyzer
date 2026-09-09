import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser


# =========================================================
# GOOGLE PAY HTML PARSER
# =========================================================

def parse_google_pay_html(uploaded_file):

    # -----------------------------------------------------
    # READ HTML
    # -----------------------------------------------------

    html_bytes = uploaded_file.getvalue()

    html = html_bytes.decode(
        "utf-8",
        errors="ignore"
    )


    # -----------------------------------------------------
    # PARSE HTML
    # -----------------------------------------------------

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    transactions = []


    # -----------------------------------------------------
    # FIND GOOGLE PAY ACTIVITY CARDS
    # -----------------------------------------------------

    cards = soup.select(
        "div.outer-cell"
    )


    # -----------------------------------------------------
    # REGEX
    # -----------------------------------------------------

    amount_pattern = re.compile(
        r"₹\s*([\d,]+(?:\.\d+)?)"
    )


    action_pattern = re.compile(
        r"^(Paid|Sent|Received|Requested)\b",
        re.IGNORECASE
    )


    # =====================================================
    # PROCESS EACH CARD
    # =====================================================

    for card in cards:


        # -------------------------------------------------
        # CHECK TITLE
        # -------------------------------------------------

        title_element = card.select_one(
            ".header-cell p"
        )


        if not title_element:

            continue


        title = title_element.get_text(
            " ",
            strip=True
        )


        if title.lower() != "google pay":

            continue


        # -------------------------------------------------
        # GET CONTENT
        # -------------------------------------------------

        content = card.select_one(
            ".content-cell.mdl-typography--body-1"
        )


        if not content:

            continue


        # -------------------------------------------------
        # GET TEXT LINES
        # -------------------------------------------------

        lines = [
            line.strip()
            for line in content.stripped_strings
            if line.strip()
        ]


        if not lines:

            continue


        # -------------------------------------------------
        # TRANSACTION DESCRIPTION
        # -------------------------------------------------

        description = lines[0]


        # -------------------------------------------------
        # IGNORE NON-TRANSACTION ACTIVITIES
        # -------------------------------------------------

        if not action_pattern.match(
            description
        ):

            continue


        # -------------------------------------------------
        # GET AMOUNT
        # -------------------------------------------------

        amount_match = amount_pattern.search(
            description
        )


        if not amount_match:

            continue


        amount = float(
            amount_match.group(1)
            .replace(",", "")
        )


        # -------------------------------------------------
        # GET DATE
        # -------------------------------------------------

        transaction_date = None


        for line in lines[1:]:

            if re.match(
                r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                line,
                re.IGNORECASE
            ):

                try:

                    transaction_date = parser.parse(
                        line
                    )

                    break

                except Exception:

                    continue


        if transaction_date is None:

            continue


        # =================================================
        # TRANSACTION TYPE
        # =================================================

        if re.match(
            r"^Received\b",
            description,
            re.IGNORECASE
        ):

            transaction_type = "Income"


        elif re.match(
            r"^Requested\b",
            description,
            re.IGNORECASE
        ):

            transaction_type = "Request"


        else:

            transaction_type = "Expense"


        # =================================================
        # MERCHANT NAME
        # =================================================

        merchant = ""


        # -------------------------------------------------
        # PAID
        # -------------------------------------------------

        if re.match(
            r"^Paid\b",
            description,
            re.IGNORECASE
        ):

            merchant_text = re.sub(
                r"^Paid\s+₹\s*[\d,]+(?:\.\d+)?\s+to\s+",
                "",
                description,
                flags=re.IGNORECASE
            )


            merchant = re.sub(
                r"\s+using\s+Bank Account\b.*$",
                "",
                merchant_text,
                flags=re.IGNORECASE
            ).strip()


        # -------------------------------------------------
        # RECEIVED
        # -------------------------------------------------

        elif re.match(
            r"^Received\b",
            description,
            re.IGNORECASE
        ):

            received_match = re.search(
                r"\bfrom\s+(.+?)(?:\s+using\s+Bank Account\b.*)?$",
                description,
                re.IGNORECASE
            )


            if received_match:

                merchant = (
                    received_match
                    .group(1)
                    .strip()
                )


        # =================================================
        # ACCOUNT
        # =================================================

        account = ""


        account_match = re.search(
            r"using\s+(Bank Account\s+.+)$",
            description,
            re.IGNORECASE
        )


        if account_match:

            account = (
                account_match
                .group(1)
                .strip()
            )


        # =================================================
        # STATUS + DETAILS
        # =================================================

        status = ""

        details = ""


        caption = card.select_one(
            ".mdl-typography--caption"
        )


        if caption:

            caption_lines = [
                line.strip()
                for line in caption.stripped_strings
                if line.strip()
            ]


            # ---------------------------------------------
            # STATUS
            # ---------------------------------------------

            valid_statuses = {
                "Completed",
                "Pending",
                "Failed"
            }


            for line in caption_lines:

                if line in valid_statuses:

                    status = line

                    break


            # ---------------------------------------------
            # DETAILS
            # ---------------------------------------------

            for index, line in enumerate(
                caption_lines
            ):

                if line.lower() == "details:":

                    if (
                        index + 1
                        < len(caption_lines)
                    ):

                        details = (
                            caption_lines[
                                index + 1
                            ]
                        )

                    break


        # =================================================
        # CATEGORY
        # =================================================

        category = categorize_transaction(
            merchant,
            description
        )


        # =================================================
        # CREATE TRANSACTION
        # =================================================

        transactions.append({

            "Transaction Date":
                transaction_date,

            "Description":
                description,

            "Merchant Name":
                merchant,

            "Amount":
                amount,

            "Transaction Type":
                transaction_type,

            "Status":
                status,

            "Account":
                account,

            "Details":
                details,

            "Category":
                category,

            "Source":
                "Google Pay",

            "Month":
                transaction_date.strftime(
                    "%Y-%m"
                ),

            "Year":
                transaction_date.year
        })


    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    df = pd.DataFrame(
        transactions
    )


    # =====================================================
    # DATA TYPE CLEANUP
    # =====================================================

    if not df.empty:

        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        )


        df["Transaction Date"] = pd.to_datetime(
            df["Transaction Date"],
            errors="coerce"
        )


        df = df.dropna(
            subset=[
                "Transaction Date",
                "Amount"
            ]
        )


    return df


# =========================================================
# BASIC CATEGORY CLASSIFICATION
# =========================================================

def categorize_transaction(
    merchant,
    description
):

    text = (
        f"{merchant} {description}"
        .lower()
    )


    # -----------------------------------------------------
    # FUEL
    # -----------------------------------------------------

    fuel_keywords = [
        "petrol",
        "fuel",
        "hpcl",
        "bpcl",
        "indian oil",
        "ioc",
        "bharat petroleum",
        "hindustan petroleum",
        "mahalaxmi energy"
    ]


    if any(
        keyword in text
        for keyword in fuel_keywords
    ):

        return "Fuel"


    # -----------------------------------------------------
    # GROCERIES
    # -----------------------------------------------------

    grocery_keywords = [
        "grocery",
        "grocer",
        "d mart",
        "dmart",
        "reliance fresh",
        "bigbasket",
        "vegetable",
        "vegetables",
        "fruit",
        "fruits",
        "super store",
        "kirana"
    ]


    if any(
        keyword in text
        for keyword in grocery_keywords
    ):

        return "Groceries"


    # -----------------------------------------------------
    # MEDICAL
    # -----------------------------------------------------

    medical_keywords = [
        "medical",
        "pharma",
        "pharmacy",
        "medico",
        "hospital",
        "clinic"
    ]


    if any(
        keyword in text
        for keyword in medical_keywords
    ):

        return "Medical"


    # -----------------------------------------------------
    # AMAZON
    # -----------------------------------------------------

    if "amazon" in text:

        return "Online Shopping"


    # -----------------------------------------------------
    # FLIPKART
    # -----------------------------------------------------

    if "flipkart" in text:

        return "Online Shopping"


    # -----------------------------------------------------
    # FOOD
    # -----------------------------------------------------

    food_keywords = [
        "restaurant",
        "hotel",
        "cafe",
        "food",
        "swiggy",
        "zomato",
        "pizza",
        "burger"
    ]


    if any(
        keyword in text
        for keyword in food_keywords
    ):

        return "Food"


    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    return "Uncategorized"