#!/usr/bin/env python
"""
Bookkeeping Categorizer - Step 7
A tool to categorize bank transactions and produce Trial Balance & P&L statements.

Steps implemented:
1. Generate sample CSV and read/display with pandas
2. Rules-based categorization with keyword matching
3. Double-entry bookkeeping (convert transactions to journal entries)
4. Trial Balance and Profit & Loss statements
5. AI categorization via OpenRouter API
6. Streamlit web interface for upload, override, and export
7. Column mapping UI for real bank CSV exports (Debit/Credit support)
"""

import pandas as pd
import os
import requests
import json
import time

# Import streamlit only when running web app
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# =============================================================================
# STEP 5: AI CATEGORIZATION SETTINGS
# Model and API configuration - easy to change at the top
# =============================================================================

# OpenRouter API settings
# Priority: Streamlit secrets > environment variable > empty string (demo mode)
# For Streamlit Cloud: set OPENROUTER_API_KEY in your app's Secrets section
# For local: set OPENROUTER_API_KEY environment variable
if STREAMLIT_AVAILABLE:
    try:
        OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    except Exception:
        OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
else:
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")  # Default model (auto-routes to free)
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# DEMO MODE: Set to True to use mock AI responses instead of real API calls
# Set DEMO_MODE=False via environment variable to use real API
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

# =============================================================================
# CHART OF ACCOUNTS
# Easy to edit at the top - organized by type for the accounting logic
# =============================================================================

# Revenue accounts - for money received (positive amounts)
REVENUE_ACCOUNTS = ["Sales Revenue", "Service Income", "Other Income"]

# Expense accounts - for money paid out (negative amounts)
EXPENSE_ACCOUNTS = [
    "Travel",
    "Meals & Entertainment",
    "Office Supplies",
    "Rent",
    "Utilities",
    "Wages",
    "Bank Fees",
    "Software & Subscriptions",
    "Marketing",
    "Professional Fees",
    "Other Expense"
]

# Asset accounts - the Bank account is the main asset for this simplified model
ASSET_ACCOUNTS = ["Bank"]

# All accounts combined - used for validation
ALL_ACCOUNTS = REVENUE_ACCOUNTS + EXPENSE_ACCOUNTS + ASSET_ACCOUNTS

# =============================================================================
# STEP 2: RULES-BASED CATEGORIZER
# Keyword matching: transaction description -> account
# All rules are defined here for easy editing
# =============================================================================

# Rules are: (keywords, account_name, account_type)
# account_type: "REVENUE", "EXPENSE", or "ASSET"
# Keywords are case-insensitive and checked if they appear in the description
# ORDER MATTERS: More specific rules should come BEFORE general ones
CATEGORIZATION_RULES = [
    # Revenue rules - for detecting income (only positive amounts should hit these)
    (["STRIPE", "PAYPAL", "PAYOUT"], "Other Income", "REVENUE"),
    (["CLIENT PAYMENT"], "Service Income", "REVENUE"),
    (["INVOICE"], "Service Income", "REVENUE"),
    (["SALE", "PRODUCT SALE"], "Sales Revenue", "REVENUE"),
    # Income keywords for transfer/credit/refund descriptions
    (["TRANSFER", "CREDIT", "REFUND"], "Other Income", "REVENUE"),

    # Professional Fees (must come before general consulting rules)
    (["DELOITTE", "KPMG", "PRICEWATERHOUSE", "AUDITOR", "ACCOUNTANT"], "Professional Fees", "EXPENSE"),

    # Marketing rules (must come before GOOGLE in software)
    (["GOOGLE ADS", "FACEBOOK ADS", "ADVERTISING", "PPC"], "Marketing", "EXPENSE"),
    (["MARKETING"], "Marketing", "EXPENSE"),

    # Software & Subscriptions rules - BUSINESS software only
    (["ADOBE", "MICROSOFT", "APPLE", "AWS"], "Software & Subscriptions", "EXPENSE"),
    (["SOFTWARE"], "Software & Subscriptions", "EXPENSE"),

    # Travel rules (must come before general PAYMENT in wages)
    (["UBER", "LYFT", "TAXI", "RIDESHARE"], "Travel", "EXPENSE"),
    (["MYKI", "OPAL", "TRANSPORT CARD"], "Travel", "EXPENSE"),

    # Office Supplies rules
    (["OFFICEWORKS", "STAPLES", "OFFICE DEPOT"], "Office Supplies", "EXPENSE"),

    # Meals & Entertainment rules (for business meals/entertainment only)
    (["MEALS", "ENTERTAINMENT", "RESTAURANT", "EATING"], "Meals & Entertainment", "EXPENSE"),

    # Rent rules
    (["RENT", "LEASE", "PREMISES"], "Rent", "EXPENSE"),

    # Utilities rules
    (["ELECTRICITY", "GAS", "WATER", "TELSTRA", "OPTUS", "VODAFONE"], "Utilities", "EXPENSE"),
    (["UTILITIES"], "Utilities", "EXPENSE"),

    # Wages rules
    (["SALARY", "WAGE", "PAYROLL"], "Wages", "EXPENSE"),

    # Bank Fees rules
    (["BANK FEES", "BANK CHARGE", "ATM FEE"], "Bank Fees", "EXPENSE"),
]

# =============================================================================
# STEP 1: Sample CSV Generation
# =============================================================================

def generate_sample_csv(filepath: str) -> None:
    """
    Create a sample CSV file with dummy bank transactions.
    Amount is positive for money IN (receipts), negative for money OUT (payments).
    """
    # Sample transactions - variety of real-world merchant names and transaction types
    sample_data = [
        # Revenue transactions (money in) - positive amounts
        {"Date": "2024-01-01", "Description": "STRIPE PAYOUT", "Amount": 2500.00},
        {"Date": "2024-01-02", "Description": "CLIENT PAYMENT - ACME Corp", "Amount": 1500.00},
        {"Date": "2024-01-03", "Description": "INVOICE #1234 - Consulting", "Amount": 3200.00},
        {"Date": "2024-01-05", "Description": "PayPal Transfer", "Amount": 850.00},
        {"Date": "2024-01-08", "Description": "Product Sale - Online Store", "Amount": 425.50},

        # Expense transactions (money out) - negative amounts
        {"Date": "2024-01-04", "Description": "UBER *EATS", "Amount": -18.75},
        {"Date": "2024-01-04", "Description": "UBER *TRIP", "Amount": -24.50},
        {"Date": "2024-01-06", "Description": "WOOLWORTHS", "Amount": -87.30},
        {"Date": "2024-01-07", "Description": "COLES SUPERMARKET", "Amount": -125.60},
        {"Date": "2024-01-09", "Description": "AWS", "Amount": -142.99},
        {"Date": "2024-01-10", "Description": "OFFICEWORKS", "Amount": -56.45},
        {"Date": "2024-01-11", "Description": "SALARY PAYMENT", "Amount": -4200.00},
        {"Date": "2024-01-12", "Description": "BANK FEES - Monthly", "Amount": -15.00},
        {"Date": "2024-01-13", "Description": "Netflix Subscription", "Amount": -15.99},
        {"Date": "2024-01-14", "Description": "Adobe Creative Cloud", "Amount": -52.99},
        {"Date": "2024-01-15", "Description": "GOOGLE ADS", "Amount": -180.00},
        {"Date": "2024-01-16", "Description": "Myki Top-up", "Amount": -50.00},
        {"Date": "2024-01-17", "Description": "Officeworks", "Amount": -32.50},
        {"Date": "2024-01-18", "Description": "Telstra Bill Payment", "Amount": -85.00},
        {"Date": "2024-01-19", "Description": "Accounting Software Subscription", "Amount": -39.00},
        {"Date": "2024-01-20", "Description": "Deloitte Consulting Fee", "Amount": -2500.00},
        {"Date": "2024-01-21", "Description": "Office Rent February", "Amount": -1800.00},
        {"Date": "2024-01-22", "Description": "Electricity Bill", "Amount": -125.40},
        {"Date": "2024-01-23", "Description": "Random Merchant XYZ", "Amount": -45.00},  # This one won't match rules - for AI step
        {"Date": "2024-01-24", "Description": "Unknown Vendor ABC", "Amount": -78.25},  # This one won't match rules - for AI step
    ]

    # Create DataFrame and save to CSV
    df = pd.DataFrame(sample_data)
    df.to_csv(filepath, index=False)
    print(f"[OK] Sample CSV generated: {filepath}")


# =============================================================================
# STEP 1: Read and Display CSV
# =============================================================================

def read_transactions(filepath: str) -> pd.DataFrame:
    """
    Read the CSV file and return a pandas DataFrame.
    """
    df = pd.read_csv(filepath)
    # Ensure Amount column is numeric
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    print(f"[OK] Loaded {len(df)} transactions from {filepath}")
    return df


def display_transactions(df: pd.DataFrame) -> None:
    """
    Display all transactions in a readable format.
    """
    print("\n" + "=" * 70)
    print("TRANSACTIONS")
    print("=" * 70)
    print(f"{'Date':<12} {'Description':<35} {'Amount':>15}")
    print("-" * 70)

    for _, row in df.iterrows():
        # Format amount with + for money in, - for money out
        amount_str = f"{row['Amount']:,.2f}"
        print(f"{row['Date']:<12} {row['Description']:<35} {amount_str:>15}")

    print("=" * 70)
    print(f"Total transactions: {len(df)}")


# =============================================================================
# STEP 2: Categorization Functions
# =============================================================================

def categorize_by_rules(description: str) -> tuple:
    """
    Apply rules-based categorization to a transaction description.

    Args:
        description: The transaction description string

    Returns:
        tuple: (account_name, account_type, confidence, matched_keyword)
               Returns ("Uncategorized", None, "low", None) if no rule matches
    """
    description_upper = description.upper()

    for keywords, account, account_type in CATEGORIZATION_RULES:
        for keyword in keywords:
            if keyword in description_upper:
                # Found a match - return the account and matched keyword
                matched_keyword = keyword
                return (account, account_type, "high", matched_keyword)

    # No rule matched - will need AI categorization in Step 5
    return ("Uncategorized", None, "low", None)


def apply_categorization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add categorization columns to the transactions DataFrame.
    """
    # SAFETY CHECK: Ensure required column exists
    if "Description" not in df.columns:
        print("[WARN] Description column missing - cannot apply rules categorization")
        # Create empty categorization columns to avoid downstream errors
        df["Account"] = "Uncategorized"
        df["AccountType"] = "EXPENSE"
        df["Confidence"] = "low"
        df["MatchedKeyword"] = None
        df["CategorizedBy"] = "Rules"
        return df

    # Apply rules to each transaction
    categorized_data = []
    for _, row in df.iterrows():
        account, account_type, confidence, keyword = categorize_by_rules(row["Description"])
        categorized_data.append({
            "Account": account,
            "AccountType": account_type,
            "Confidence": confidence,
            "MatchedKeyword": keyword,
            "CategorizedBy": "Rules"  # Track which layer categorized this
        })

    # Convert to DataFrame and join with original
    categorized_df = pd.DataFrame(categorized_data)
    result_df = pd.concat([df.reset_index(drop=True), categorized_df], axis=1)

    # POST-PROCESSING: Fix account type mismatches based on amount sign
    # Rules match keywords but don't check amount sign - e.g., "TRANSFER" matches
    # both incoming (positive) and outgoing (negative) transfers
    for i, row in result_df.iterrows():
        amt = row["Amount"]
        acct = row["Account"]
        if acct in REVENUE_ACCOUNTS and amt < 0:
            # Rule matched revenue keyword but amount is negative (money out)
            result_df.loc[i, "Account"] = "Other Expense"
            result_df.loc[i, "AccountType"] = "EXPENSE"
            result_df.loc[i, "Confidence"] = "low"
            print(f"[CORRECTED] '{row['Description'][:40]}...' amount={amt} -> 'Other Expense' (was '{acct}')")
        elif acct in EXPENSE_ACCOUNTS and amt >= 0:
            # Rule matched expense keyword but amount is positive (money in)
            result_df.loc[i, "Account"] = "Other Income"
            result_df.loc[i, "AccountType"] = "REVENUE"
            result_df.loc[i, "Confidence"] = "low"
            print(f"[CORRECTED] '{row['Description'][:40]}...' amount={amt} -> 'Other Income' (was '{acct}')")

    return result_df


def display_categorized_transactions(df: pd.DataFrame, title: str = "CATEGORIZED TRANSACTIONS") -> None:
    """
    Display transactions with their assigned accounts and categorization method.
    """
    print("\n" + "=" * 115)
    print(title)
    print("=" * 115)
    print(f"{'Date':<12} {'Description':<35} {'Amount':>12} {'Account':<25} {'Confidence':>10} {'Method':>10}")
    print("-" * 115)

    for _, row in df.iterrows():
        account = row["Account"] if pd.notna(row["Account"]) else "Uncategorized"
        confidence = row["Confidence"] if pd.notna(row["Confidence"]) else "low"
        method = row["CategorizedBy"] if "CategorizedBy" in row and pd.notna(row["CategorizedBy"]) else "Rules"
        amount_str = f"{row['Amount']:>10,.2f}"
        print(f"{row['Date']:<12} {row['Description']:<35} {amount_str} {account:<25} {confidence:>10} {method:>10}")

    print("=" * 115)

    # Show summary of categorization
    categorized = len(df[df["Account"] != "Uncategorized"])
    total = len(df)
    print(f"Categorized: {categorized}/{total} ({100*categorized/total:.1f}%)")
    if "CategorizedBy" in df.columns:
        ai_count = len(df[df["CategorizedBy"] == "AI"]) if "AI" in df["CategorizedBy"].values else 0
        rules_count = categorized - ai_count
        print(f"By Rules: {rules_count}, By AI: {ai_count}")
    print(f"Uncategorized: {total - categorized} (awaiting AI layer)")


# =============================================================================
# STEP 3: Double-Entry Bookkeeping
# Convert transactions to debit/credit entries
# =============================================================================

def create_journal_entries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert categorized transactions into double-entry journal entries.

    Double-entry rules (simplified bank-feed model):
    - Money OUT (negative amount) for an expense: Debit Expense, Credit Bank
    - Money IN (positive amount) that is revenue: Debit Bank, Credit Revenue

    Each entry creates TWO rows: one debit and one credit.
    """
    journal_entries = []

    for idx, row in df.iterrows():
        amount = row["Amount"]
        account = row["Account"]

        # Skip uncategorized accounts for now - they'll be handled after AI layer
        if account == "Uncategorized":
            continue

        account_type = row["AccountType"]

        if amount < 0:  # Money OUT (expense payment)
            # Debit the expense account, Credit Bank
            debit_account = account
            credit_account = "Bank"
            entry_amount = abs(amount)  # Positive amount for the entry
        else:  # Money IN (revenue receipt)
            # Debit Bank, Credit the revenue account
            debit_account = "Bank"
            credit_account = account
            entry_amount = amount

        # Create debit entry
        journal_entries.append({
            "Date": row["Date"],
            "Description": row["Description"],
            "Account": debit_account,
            "Debit": entry_amount,
            "Credit": 0.0,
            "EntryType": "Debit"
        })

        # Create credit entry
        journal_entries.append({
            "Date": row["Date"],
            "Description": row["Description"],
            "Account": credit_account,
            "Debit": 0.0,
            "Credit": entry_amount,
            "EntryType": "Credit"
        })

    return pd.DataFrame(journal_entries)


def display_journal_entries(df: pd.DataFrame) -> None:
    """
    Display all journal entries in a readable format.
    """
    print("\n" + "=" * 80)
    print("JOURNAL ENTRIES (Double-Entry Bookkeeping)")
    print("=" * 80)
    print(f"{'Date':<12} {'Account':<25} {'Debit':>12} {'Credit':>12}")
    print("-" * 80)

    for _, row in df.iterrows():
        # Only show non-zero amounts
        if row["Debit"] > 0:
            debit_str = f"{row['Debit']:>10,.2f}"
            print(f"{row['Date']:<12} {row['Account']:<25} {debit_str} {'':>12}")
        elif row["Credit"] > 0:
            credit_str = f"{row['Credit']:>12,.2f}"
            print(f"{row['Date']:<12} {row['Account']:<25} {'':>12} {credit_str}")

    print("=" * 80)
    total_debits = df["Debit"].sum()
    total_credits = df["Credit"].sum()
    print(f"Total Debits:   {total_debits:>15,.2f}")
    print(f"Total Credits:  {total_credits:>15,.2f}")
    print(f"Balanced: {'YES' if abs(total_debits - total_credits) < 0.01 else 'NO'}")


# =============================================================================
# STEP 4: Trial Balance and Profit & Loss
# =============================================================================

def build_trial_balance(journal_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build trial balance from journal entries.

    Aggregates debit and credit amounts by account.
    Shows the balance check for accountants.
    """
    # Group by account and sum debits/credits
    trial_balance = journal_df.groupby("Account").agg({
        "Debit": "sum",
        "Credit": "sum"
    }).reset_index()

    # Calculate the balance (debit - credit) for each account
    trial_balance["Balance"] = trial_balance["Debit"] - trial_balance["Credit"]

    # Round to 2 decimal places
    trial_balance["Debit"] = trial_balance["Debit"].round(2)
    trial_balance["Credit"] = trial_balance["Credit"].round(2)
    trial_balance["Balance"] = trial_balance["Balance"].round(2)

    return trial_balance


def build_profit_and_loss(categorized_df: pd.DataFrame) -> dict:
    """
    Build Profit & Loss statement from categorized transactions.

    P&L shows:
    - Revenue accounts (total money in)
    - Expense accounts (total money out)
    - Net Profit/Loss = Revenue - Expenses
    """
    # Filter to categorized transactions only
    valid_df = categorized_df[categorized_df["Account"] != "Uncategorized"]

    # Separate revenue and expense totals
    revenue_df = valid_df[valid_df["AccountType"] == "REVENUE"]
    expense_df = valid_df[valid_df["AccountType"] == "EXPENSE"]

    # Sum by account
    revenue_by_account = revenue_df.groupby("Account")["Amount"].sum().to_dict()
    expense_by_account = expense_df.groupby("Account")["Amount"].sum().to_dict()

    # Total revenue = sum of positive amounts
    total_revenue = sum(abs(v) for v in revenue_by_account.values())

    # Total expenses = sum of negative amounts (made positive)
    total_expenses = sum(abs(v) for v in expense_by_account.values())

    net_profit = total_revenue - total_expenses

    return {
        "revenue": revenue_by_account,
        "expenses": expense_by_account,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit
    }


def display_trial_balance(trial_balance: pd.DataFrame) -> None:
    """
    Display trial balance in a formatted table.
    """
    print("\n" + "=" * 60)
    print("TRIAL BALANCE")
    print("=" * 60)
    print(f"{'Account':<25} {'Debit':>12} {'Credit':>12} {'Balance':>12}")
    print("-" * 60)

    for _, row in trial_balance.iterrows():
        # Format with appropriate alignment
        debit_str = f"{row['Debit']:>10,.2f}" if row['Debit'] > 0 else ""
        credit_str = f"{row['Credit']:>12,.2f}" if row['Credit'] > 0 else ""
        balance_str = f"{row['Balance']:>12,.2f}"
        print(f"{row['Account']:<25} {debit_str} {credit_str} {balance_str}")

    print("=" * 60)

    total_debits = trial_balance["Debit"].sum()
    total_credits = trial_balance["Credit"].sum()

    print(f"{'TOTALS':<25} {total_debits:>12,.2f} {total_credits:>12,.2f}")

    # CRITICAL VALIDATION: Check if trial balance balances
    if abs(total_debits - total_credits) < 0.01:
        print(f"\n[VALIDATION PASSED] Debits = Credits (Balanced Trial Balance)")
    else:
        print(f"\n[ERROR] Trial Balance does NOT balance!")
        print(f"  Difference: {abs(total_debits - total_credits):,.2f}")


def display_profit_and_loss(pnl: dict) -> None:
    """
    Display Profit & Loss statement in a formatted table.
    """
    print("\n" + "=" * 50)
    print("PROFIT & LOSS STATEMENT")
    print("=" * 50)

    print("\nREVENUE")
    print("-" * 50)
    for account, amount in pnl["revenue"].items():
        print(f"  {account:<20} {abs(amount):>15,.2f}")

    print(f"  {'TOTAL REVENUE':<20} {pnl['total_revenue']:>15,.2f}")

    print("\nEXPENSES")
    print("-" * 50)
    for account, amount in pnl["expenses"].items():
        print(f"  {account:<20} {abs(amount):>15,.2f}")

    print(f"  {'TOTAL EXPENSES':<20} {pnl['total_expenses']:>15,.2f}")

    print("\n" + "=" * 50)
    net = pnl["net_profit"]
    result_type = "Profit" if net >= 0 else "Loss"
    print(f"NET {result_type}: {abs(net):>15,.2f}")
    print("=" * 50)


# =============================================================================
# STEP 5: AI Categorization
# Batch requests to OpenRouter API for uncategorized transactions
# =============================================================================

def mock_ai_categorization(descriptions: list, amounts: list = None) -> list:
    """
    Mock AI categorization for testing without an API key.
    Simulates what a real AI would return.
    """
    # Mock responses for our test data
    # WHSMITH and WW/WW Metro are general retailers -> Other Expense (not office supplies)
    # YUM BOX matches "RESTAURANT" or "EATING" keywords but we handle explicitly
    # Transfers with positive amounts -> Other Income, negative -> Other Expense
    mock_responses = {
        "WOOLWORTHS": "Other Expense",
        "COLES SUPERMARKET": "Other Expense",
        "Netflix Subscription": "Other Expense",
        "WHSMITH": "Other Expense",
        "WW": "Other Expense",
        "YUM BOX": "Meals & Entertainment",
        "Random Merchant XYZ": "Travel",
        "Unknown Vendor ABC": "Office Supplies",
        "TRANSFER": "Other Income",  # Will be corrected based on amount sign
        "CREDIT": "Other Income",    # Will be corrected based on amount sign
        "REFUND": "Other Income",    # Will be corrected based on amount sign
    }

    output = []
    for idx, desc in enumerate(descriptions):
        # Find matching mock response
        account = "Uncategorized"
        confidence = "low"
        for keyword, acct in mock_responses.items():
            if keyword.upper() in desc.upper():
                account = acct
                confidence = "medium"  # AI confidence is typically medium
                break

        # For vague merchants without a specific match, use amount to decide revenue vs expense
        if account == "Uncategorized" and amounts is not None and idx < len(amounts):
            if amounts[idx] >= 0:
                account = "Other Income"  # Positive = money in = revenue
            else:
                account = "Other Expense"  # Negative = money out = expense

        output.append({"account": account, "confidence": confidence})

    return output


def categorize_with_ai(descriptions: list, amounts: list = None) -> list:
    """
    Call OpenRouter API to categorize uncategorized transactions.
    Falls back to mock if no API key is set.

    Args:
        descriptions: List of transaction descriptions to categorize
        amounts: Optional list of amounts to help determine revenue vs expense

    Returns:
        List of dicts with account, confidence for each description
    """
    # Check for DEMO_MODE or valid API key - use mock if demo mode or no key
    if DEMO_MODE or not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == "":
        print("[INFO] Using MOCK AI categorization for demonstration")
        return mock_ai_categorization(descriptions, amounts)

    # Build the prompt with all descriptions and valid accounts
    accounts_list = ", ".join(ALL_ACCOUNTS)

    # Format descriptions with amounts for better context
    desc_list = "\n".join([f"{i+1}. {desc} (Amount: {amounts[i] if i < len(amounts) else 'unknown'})" for i, desc in enumerate(descriptions)])

    prompt = f"""You are an accounting assistant. Categorize each transaction into one of the following accounts ONLY: {accounts_list}

RULES:
1. Amount > 0 (money IN) → REVENUE accounts ONLY: Sales Revenue, Service Income, Other Income
2. Amount < 0 (money OUT) → EXPENSE accounts ONLY: Travel, Meals & Entertainment, Office Supplies, Rent, Utilities, Wages, Bank Fees, Software & Subscriptions, Marketing, Professional Fees, Other Expense

STRATEGY - try these in order:
- Try to match the description to a SPECIFIC account first (e.g., "UBER" → Travel, "OFFICEWORKS" → Office Supplies, "NETFLIX" → Software & Subscriptions, "TELSTRA" → Utilities)
- If the description is a transfer, payment, or unclear: choose "Other Expense" for money OUT (negative) or "Other Income" for money IN (positive)
- NEVER put money IN (positive amount) into an EXPENSE account
- NEVER put money OUT (negative amount) into a REVENUE account

Return ONLY valid JSON with this format (no other text):
{{
  "results": [
    {{"description_index": 1, "account": "Account Name", "confidence": "high|medium|low"}},
    {{"description_index": 2, "account": "Account Name", "confidence": "high|medium|low"}},
    ...
  ]
}}

Transactions to categorize:
{desc_list}
"""

    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8501",
                    "X-Title": "Bookkeeping Categorizer"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=30
            )

            # Success - parse the response
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON safely
                parsed = json.loads(content)
                ai_results = parsed.get("results", [])

                # Build output list in correct order
                output = []
                for i in range(len(descriptions)):
                    account = "Uncategorized"
                    confidence = "low"
                    for r in ai_results:
                        if r.get("description_index") == i + 1:
                            if r.get("account") in ALL_ACCOUNTS:
                                account = r["account"]
                                confidence = r.get("confidence", "low")
                            break
                    output.append({"account": account, "confidence": confidence})
                return output

            # Rate limited - wait and retry with backoff
            if response.status_code == 429:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"[WARNING] Rate limited (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            # Other error - log and fallback
            print(f"[ERROR] API returned status {response.status_code}")
            break

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse AI response as JSON: {e}")
            # Fallback to amount-based categorization
            return [{"account": "Other Income" if (amounts is not None and idx < len(amounts) and amounts[idx] >= 0) else "Other Expense", "confidence": "medium"} for idx in range(len(descriptions))]

        except Exception as e:
            print(f"[ERROR] AI categorization failed: {e}")
            # Only retry on network errors, not parse errors
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[RETRY] Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            break

    # All retries exhausted - fallback to amount-based categorization
    print("[WARN] AI categorization failed - using amount-based fallback")
    return [{"account": "Other Income" if (amounts is not None and idx < len(amounts) and amounts[idx] >= 0) else "Other Expense", "confidence": "medium"} for idx in range(len(descriptions))]


def apply_ai_categorization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply AI categorization to uncategorized transactions.
    Returns updated DataFrame with AI results.
    """
    # SAFETY CHECK: Ensure required columns exist
    if "Account" not in df.columns:
        print("[WARN] Account column missing - cannot apply AI categorization")
        return df

    # Find uncategorized rows
    uncategorized_mask = df["Account"] == "Uncategorized"
    uncategorized_df = df[uncategorized_mask]

    if len(uncategorized_df) == 0:
        return df  # Nothing to categorize

    print(f"\n[INFO] Calling AI for {len(uncategorized_df)} uncategorized transactions...")

    # Get descriptions and amounts, then categorize
    descriptions = uncategorized_df["Description"].tolist()
    amounts = uncategorized_df["Amount"].tolist()  # Pass amounts for revenue/expense decision
    ai_results = categorize_with_ai(descriptions, amounts)

    # Update the DataFrame
    for idx, (i, row) in enumerate(uncategorized_df.iterrows()):
        account = ai_results[idx]["account"]
        confidence = ai_results[idx]["confidence"]

        df.loc[i, "Confidence"] = confidence
        df.loc[i, "MatchedKeyword"] = "AI"  # Mark as AI-categorized
        df.loc[i, "CategorizedBy"] = "AI"  # Track that AI categorized this

        # CORRECTION: Validate account type matches amount sign
        # Amount > 0 = money IN = REVENUE accounts
        # Amount < 0 = money OUT = EXPENSE accounts
        amt = df.loc[i, "Amount"]

        # Determine if account type matches amount sign
        ai_account = ai_results[idx]["account"]
        is_revenue_account = account in REVENUE_ACCOUNTS
        is_expense_account = account in EXPENSE_ACCOUNTS

        # If AI chose account type that doesn't match amount sign, correct it
        if amt >= 0 and is_expense_account:
            # Positive amount but AI chose expense - change to Other Income
            account = "Other Income"
            print(f"[CORRECTED REVENUE] '{row['Description'][:40]}...' amount={amt} -> '{account}' (was '{ai_account}')")
        elif amt < 0 and is_revenue_account:
            # Negative amount but AI chose revenue - change to Other Expense
            account = "Other Expense"
            print(f"[CORRECTED EXPENSE] '{row['Description'][:40]}...' amount={amt} -> '{account}' (was '{ai_account}')")
        elif account == "Uncategorized":
            # For uncategorized, categorize based on amount sign
            account = "Other Income" if amt >= 0 else "Other Expense"
            print(f"[UNCATEGORIZED] '{row['Description'][:40]}...' amount={amt} -> '{account}'")

        df.loc[i, "Account"] = account
        df.loc[i, "AccountType"] = "REVENUE" if account in REVENUE_ACCOUNTS else "EXPENSE"

    return df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
        # CLI mode - run all steps
        SAMPLE_FILE = "sample_transactions.csv"

        # Step 1: Generate and load transactions
        generate_sample_csv(SAMPLE_FILE)
        transactions_df = read_transactions(SAMPLE_FILE)
        display_transactions(transactions_df)

        # Step 2: Apply rules-based categorization
        categorized_df = apply_categorization(transactions_df)
        display_categorized_transactions(categorized_df)

        # Step 3: Create double-entry journal entries
        journal_df = create_journal_entries(categorized_df)
        display_journal_entries(journal_df)

        # Step 4: Build and display Trial Balance and P&L
        trial_balance = build_trial_balance(journal_df)
        display_trial_balance(trial_balance)

        pnl = build_profit_and_loss(categorized_df)
        display_profit_and_loss(pnl)

        # Step 5: Apply AI categorization
        categorized_df = apply_ai_categorization(categorized_df)
        display_categorized_transactions(categorized_df, "TRANSACTIONS AFTER AI CATEGORIZATION")

        # Rebuild journal entries and reports with AI results
        journal_df = create_journal_entries(categorized_df)
        display_journal_entries(journal_df)

        trial_balance = build_trial_balance(journal_df)
        display_trial_balance(trial_balance)

        pnl = build_profit_and_loss(categorized_df)
        display_profit_and_loss(pnl)