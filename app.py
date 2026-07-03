#!/usr/bin/env python
"""
Streamlit web app for Bookkeeping Categorizer.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import warnings

# Import the core functions from bookkeeping_categorizer
from bookkeeping_categorizer import (
    REVENUE_ACCOUNTS, EXPENSE_ACCOUNTS, ALL_ACCOUNTS,
    apply_categorization, apply_ai_categorization,
    create_journal_entries, build_trial_balance, build_profit_and_loss,
    DEMO_MODE
)

# =============================================================================
# PAGE CONFIG - must be the first Streamlit command
# =============================================================================

st.set_page_config(
    page_title="Bookkeeping Categorizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM CSS - theme-aware (works in both light & dark mode)
# =============================================================================

st.markdown("""
<style>
    /* ======== LAYOUT & STRUCTURE ======== */

    .app-header {
        padding: 1.5rem 0 0.5rem 0;
        border-bottom: 1px solid var(--border-color, #d0d0d0);
        margin-bottom: 1.5rem;
    }
    .app-header h1 { font-size: 2rem; font-weight: 700; margin: 0; padding: 0; }
    .app-header .subtitle { font-size: 1rem; margin-top: 0.25rem; }

    .section-header { font-size: 1.15rem; font-weight: 700; margin: 1.5rem 0 0.75rem 0; }

    .footer {
        text-align: center; padding: 2rem 0 1rem 0;
        font-size: 0.8rem; border-top: 1px solid var(--border-color, #d0d0d0); margin-top: 2rem;
    }

    .dataframe { font-size: 0.85rem; }

    .sidebar-section { margin-bottom: 1.5rem; }
    .sidebar-section h3 {
        font-size: 0.85rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.05em; margin-bottom: 0.5rem;
    }
    .account-item { font-size: 0.85rem; padding: 0.15rem 0; font-weight: 600; }
    .account-item.revenue { color: #008300; font-weight: 600; }
    .account-item.expense { color: #d03b3b; font-weight: 600; }

    .balance-check { padding: 0.75rem 1rem; border-radius: 6px; font-weight: 500; margin: 1rem 0; }
    .balance-check.valid { background: #e8f5e9; color: #1b5e20; border: 1px solid #81c784; }
    .balance-check.invalid { background: #fce4ec; color: #b71c1c; border: 1px solid #e57373; }

    /* ======== LIGHT BLUE ACCENTS ======== */

    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { font-weight: 500; font-size: 0.9rem; padding: 0.5rem 1rem; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #6da7ec !important; }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { border-bottom-color: #6da7ec !important; }
    .stTabs [class*="StyledActiveTabIndicator"] { background-color: #6da7ec !important; }

    [data-testid="stSidebarNavItems"] a:hover { color: #6da7ec !important; }
    [data-testid="stSidebarNavItems"] a:focus,
    [data-testid="stSidebarNavItems"] a[data-testid*="active"] { color: #6da7ec !important; border-left-color: #6da7ec !important; }
    [data-testid="stSidebarNavItems"] svg { fill: #6da7ec !important; }

    [data-testid="stSidebarHeader"] { background-color: #6da7ec !important; }
    [data-testid="stSidebarHeader"] * { color: #ffffff !important; }
    section[data-testid="stSidebar"] > div:first-child { background: linear-gradient(180deg, #6da7ec 0%, #5b9bd5 100%) !important; }
    section[data-testid="stSidebar"] > div:first-child * { color: #ffffff !important; }
    button[data-testid="stSidebarCollapseButton"], button[data-testid="stSidebarCollapseButton"] svg { color: #ffffff !important; fill: #ffffff !important; }
    [data-testid="stSidebarHeader"] img { filter: brightness(0) invert(1) !important; }

    [data-testid="stFileUploader"] { border-color: #6da7ec !important; }
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] { border-color: #6da7ec !important; }
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover { border-color: #5b9bd5 !important; }
    [data-testid="stFileUploader"] button { background-color: #6da7ec !important; border-color: #6da7ec !important; color: #ffffff !important; }
    [data-testid="stFileUploader"] button:hover { background-color: #5b9bd5 !important; border-color: #5b9bd5 !important; }

    .stButton button, .stDownloadButton button { background-color: #6da7ec !important; border-color: #6da7ec !important; color: #ffffff !important; }
    .stButton button:hover, .stDownloadButton button:hover { background-color: #5b9bd5 !important; border-color: #5b9bd5 !important; }
    .stButton button p, .stDownloadButton button p { color: #ffffff !important; }

    a { color: #6da7ec !important; }

    /* ======== LIGHT MODE ======== */
    @media (prefers-color-scheme: light) {
        .sidebar-section h3 { color: #555555 !important; }
        .section-header { color: #111111 !important; }
        .app-header h1 { color: #111111 !important; }
        .app-header .subtitle { color: #2d2d2d !important; }
        .stTabs [data-baseweb="tab"] { color: #111111 !important; }
        .footer { color: #555555 !important; }
    }

    /* ======== DARK MODE ======== */
    @media (prefers-color-scheme: dark) {
        .sidebar-section h3 { color: #bbbbbb !important; }
        .section-header { color: #ffffff !important; }
        .app-header h1 { color: #ffffff !important; }
        .app-header .subtitle { color: #cccccc !important; }
        .stTabs [data-baseweb="tab"] { color: #cccccc !important; }
        .footer { color: #999999 !important; }
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# COLUMN MAPPING UI
# =============================================================================

def map_columns_ui(df: pd.DataFrame) -> tuple:
    """
    UI for mapping CSV columns to the tool's internal format.

    Handles two modes:
    1. Single Amount column (positive = money in, negative = money out)
    2. Separate Debit/Credit columns (Credit = positive, Debit = negative)

    Returns: (mapped_df, success) where mapped_df has Date/Description/Amount columns
    """
    st.markdown('<div class="section-header">Column Mapping</div>', unsafe_allow_html=True)

    # Get available columns from the uploaded file
    all_columns = df.columns.tolist()

    # Show the columns found in the uploaded file
    st.markdown(f"**Columns detected:** {', '.join(all_columns)}")

    # Radio button to select amount mode
    amount_mode = st.radio(
        "Amount Format",
        options=["Single Amount column (positive=in, negative=out)",
                "Separate Debit/Credit columns (money out/in)"],
        help="Choose how your bank exports amount data. Most banks use separate Debit/Credit columns.",
        horizontal=True
    )

    # Initialize mapping variables
    date_col, desc_col = None, None
    amount_col, debit_col, credit_col = None, None, None

    # Dropdown columns for mapping
    col1, col2 = st.columns(2)
    with col1:
        date_col = st.selectbox(
            "Select Date column",
            options=[""] + all_columns,
            help="The column containing transaction dates"
        )
        desc_col = st.selectbox(
            "Select Description column",
            options=[""] + all_columns,
            help="The column containing transaction descriptions"
        )

    with col2:
        if amount_mode == "Single Amount column (positive=in, negative=out)":
            amount_col = st.selectbox(
                "Select Amount column",
                options=[""] + all_columns,
                help="Positive values = money in, Negative = money out"
            )
        else:
            debit_col = st.selectbox(
                "Select Debit column (money out)",
                options=[""] + all_columns,
                help="Money leaving your account (expenses)"
            )
            credit_col = st.selectbox(
                "Select Credit column (money in)",
                options=[""] + all_columns,
                help="Money entering your account (income)"
            )

    # Validate required selections
    required_selected = date_col and desc_col
    if amount_mode == "Single Amount column (positive=in, negative=out)":
        required_selected = required_selected and amount_col
    else:
        required_selected = required_selected and debit_col and credit_col

    if not required_selected:
        st.info("Please select all required column mappings to proceed.")
        return None, False

    # Transform the data to standard format
    try:
        mapped_df = pd.DataFrame()

        # Map Date column
        mapped_df["Date"] = df[date_col].copy()

        # Map Description column
        mapped_df["Description"] = df[desc_col].copy()

        # Handle Amount column(s) - convert to numeric, handle different date formats
        if amount_mode == "Single Amount column (positive=in, negative=out)":
            mapped_df["Amount"] = pd.to_numeric(df[amount_col], errors="coerce")
        else:
            # Combine Debit/Credit into signed Amount
            # Credit (money in) = positive, Debit (money out) = negative
            debit_vals = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
            credit_vals = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
            mapped_df["Amount"] = credit_vals - debit_vals  # Credit positive, Debit negative

        # Parse dates (handle various formats) - suppress the inferred format warning
        # Use dayfirst=True to correctly parse DD/MM/YYYY (Australian) format
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mapped_df["Date"] = pd.to_datetime(mapped_df["Date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")

        # Remove rows with missing critical data - show detailed info for debugging
        original_count = len(mapped_df)

        # Check for NaN values in each column before dropna
        date_nan = mapped_df["Date"].isna().sum()
        desc_nan = mapped_df["Description"].isna().sum()
        amount_nan = mapped_df["Amount"].isna().sum()

        if date_nan > 0 or desc_nan > 0 or amount_nan > 0:
            st.warning(f"⚠️ {date_nan} date, {desc_nan} description, {amount_nan} amount issues")

        mapped_df_clean = mapped_df.dropna(subset=["Date", "Description", "Amount"])
        if len(mapped_df_clean) < original_count:
            skipped = original_count - len(mapped_df_clean)
            st.info(f"Skipped {skipped} rows with missing data")

        mapped_df = mapped_df_clean
        # Show a preview if mapping succeeded
        st.success(f"✅ Mapped {len(mapped_df)} transactions — ready to categorize")
        with st.expander("Preview mapped data"):
            st.dataframe(mapped_df.head(5), use_container_width=True)
        return mapped_df, True

    except Exception as e:
        st.error(f"Error mapping columns: {e}")
        return None, False


# =============================================================================
# HEADER
# =============================================================================

st.markdown("""
<div class="app-header">
    <h1>📊 AI-Assisted Bookkeeping Categorizer</h1>
    <div class="subtitle">
        Upload a bank CSV to automatically categorize transactions, view a trial balance, and generate a Profit &amp; Loss statement — powered by rules and AI.
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>Settings</h3>", unsafe_allow_html=True)

    use_ai = st.checkbox("Enable AI Categorization", value=not DEMO_MODE)
    st.info(f"Demo Mode: {'ON' if DEMO_MODE else 'OFF'}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>Chart of Accounts</h3>", unsafe_allow_html=True)

    with st.expander("Revenue Accounts", expanded=True):
        for acc in REVENUE_ACCOUNTS:
            st.markdown(f'<div class="account-item revenue">💰 {acc}</div>', unsafe_allow_html=True)

    with st.expander("Expense Accounts", expanded=True):
        for acc in EXPENSE_ACCOUNTS:
            st.markdown(f'<div class="account-item expense">💸 {acc}</div>', unsafe_allow_html=True)

    with st.expander("Asset Accounts", expanded=False):
        st.markdown('<div class="account-item">🏦 Bank</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("<h3>About</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style="font-size:0.85rem;">
        A portfolio project demonstrating automated bookkeeping with Python,
        pandas, and Streamlit. Uses rules-based keyword matching plus AI
        categorization for uncategorized transactions.
        </p>
        """, unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Tabs
tab_upload, tab_transactions, tab_trial, tab_pnl = st.tabs([
    "📂 Upload &amp; Map",
    "📋 Transactions",
    "⚖️ Trial Balance",
    "📈 Profit &amp; Loss"
])

# =============================================================================
# TAB 1: UPLOAD & MAP
# =============================================================================

with tab_upload:
    st.markdown('<div class="section-header">Upload Bank CSV</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Any bank CSV export — map your columns in the next step"
    )

    if uploaded_file is not None:
        # Read the uploaded CSV with automatic delimiter detection
        try:
            sample = uploaded_file.read(4096).decode('utf-8')
            uploaded_file.seek(0)

            import csv
            sniffer = csv.Sniffer()
            detected_sep = sniffer.sniff(sample).delimiter

            raw_df = pd.read_csv(uploaded_file, sep=detected_sep)
            st.success(f"✅ Loaded {len(raw_df)} rows (delimiter: '{detected_sep}')")

            st.markdown("### Raw Data Preview")
            st.dataframe(raw_df.head(5), use_container_width=True)

        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            uploaded_file = None

    if uploaded_file is not None:
        # Column mapping UI
        st.markdown("---")
        mapped_df, mapping_success = map_columns_ui(raw_df)

        if mapping_success and mapped_df is not None:
            # Apply categorization
            with st.spinner("Categorizing transactions..."):
                categorized_df = apply_categorization(mapped_df.copy())

                if "Account" not in categorized_df.columns:
                    st.error("Error: Account column missing during categorization.")
                    st.stop()

                if use_ai:
                    categorized_df = apply_ai_categorization(categorized_df)

            # Store in session state
            st.session_state["categorized_df"] = categorized_df
            st.session_state["data_ready"] = True

            st.success("✅ Categorization complete!")
            st.balloons()

            # Quick summary
            st.markdown("### Quick Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Transactions",
                    len(categorized_df),
                    delta=None
                )
            with col2:
                categorized_count = len(categorized_df[categorized_df["Account"] != "Uncategorized"])
                st.metric(
                    "Categorized",
                    f"{categorized_count}/{len(categorized_df)}",
                    delta=f"{100*categorized_count//len(categorized_df)}%"
                )
            with col3:
                revenue_total = categorized_df[categorized_df["AccountType"] == "REVENUE"]["Amount"].sum()
                st.metric(
                    "Total Revenue",
                    f"${revenue_total:,.2f}",
                    delta_color="normal"
                )
            with col4:
                expense_total = abs(categorized_df[categorized_df["AccountType"] == "EXPENSE"]["Amount"].sum())
                st.metric(
                    "Total Expenses",
                    f"${expense_total:,.2f}",
                    delta_color="inverse"
                )

    else:
        st.info("📄 Upload a CSV file to get started. You can also download the sample CSV to try it out.")

        # Sample data section
        st.markdown("---")
        st.markdown("### Need sample data?")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📥 Download Sample CSV", use_container_width=True):
                sample_data = pd.DataFrame([
                    {"Date": "2024-01-01", "Description": "STRIPE PAYOUT", "Amount": 2500.00},
                    {"Date": "2024-01-02", "Description": "CLIENT PAYMENT - ACME Corp", "Amount": 1500.00},
                    {"Date": "2024-01-03", "Description": "INVOICE #1234 - Consulting", "Amount": 3200.00},
                    {"Date": "2024-01-04", "Description": "UBER *EATS", "Amount": -18.75},
                    {"Date": "2024-01-05", "Description": "WOOLWORTHS", "Amount": -87.30},
                    {"Date": "2024-01-06", "Description": "AWS", "Amount": -142.99},
                    {"Date": "2024-01-07", "Description": "OFFICEWORKS", "Amount": -56.45},
                    {"Date": "2024-01-08", "Description": "SALARY PAYMENT", "Amount": -4200.00},
                    {"Date": "2024-01-09", "Description": "Netflix Subscription", "Amount": -15.99},
                    {"Date": "2024-01-10", "Description": "Deloitte Consulting Fee", "Amount": -2500.00},
                ])
                csv = sample_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Sample CSV",
                    data=csv,
                    file_name="sample_transactions.csv",
                    mime="text/csv"
                )
        with col2:
            st.markdown("""
            <p style="font-size:0.9rem; margin:0;">
                A sample CSV with 10 transactions (5 revenue, 5 expense) covering
                various categories. Download it and upload to explore the tool.
            </p>
            """, unsafe_allow_html=True)


# =============================================================================
# TAB 2: TRANSACTIONS
# =============================================================================

with tab_transactions:
    if "data_ready" not in st.session_state or not st.session_state["data_ready"]:
        st.info("📂 Upload a CSV file in the **Upload & Map** tab first to see transactions here.")
    else:
        categorized_df = st.session_state["categorized_df"]

        st.markdown('<div class="section-header">Categorized Transactions</div>', unsafe_allow_html=True)

        # Summary metrics row
        total_rev = categorized_df[categorized_df["AccountType"] == "REVENUE"]["Amount"].sum()
        total_exp = abs(categorized_df[categorized_df["AccountType"] == "EXPENSE"]["Amount"].sum())
        net = total_rev - total_exp

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("Total Revenue", f"${total_rev:,.2f}", delta_color="normal")
        with mcol2:
            st.metric("Total Expenses", f"${total_exp:,.2f}", delta_color="inverse")
        with mcol3:
            st.metric("Net Profit", f"${net:,.2f}", delta=f"{'Profit' if net>=0 else 'Loss'}")
        with mcol4:
            cat_count = len(categorized_df[categorized_df["Account"] != "Uncategorized"])
            st.metric("Categorized", f"{cat_count}/{len(categorized_df)}")

        st.markdown("---")

        # Editable transactions table
        edited_rows = []
        for idx, row in categorized_df.iterrows():
            cols = st.columns([1.5, 3.5, 1.5, 2.5, 1.2, 1])
            with cols[0]:
                st.write(row["Date"])
            with cols[1]:
                st.write(row["Description"])
            with cols[2]:
                amt = row["Amount"]
                color = "green" if amt >= 0 else "red"
                st.markdown(f":{color}[${amt:,.2f}]")
            with cols[3]:
                all_options = [""] + ALL_ACCOUNTS
                current = row["Account"] if row["Account"] != "Uncategorized" else ""
                try:
                    current_idx = all_options.index(current) if current in all_options else 0
                except:
                    current_idx = 0

                new_account = st.selectbox(
                    "Account",
                    options=all_options,
                    index=current_idx,
                    key=f"acc_{idx}",
                    label_visibility="collapsed"
                )

                original_account = row["Account"]
                row_data = row.to_dict()
                if new_account and new_account != original_account:
                    row_data["Account"] = new_account
                    row_data["Confidence"] = "manual"
                    row_data["AccountType"] = (
                        "REVENUE" if new_account in REVENUE_ACCOUNTS else "EXPENSE"
                    )
                    row_data["CategorizedBy"] = "Manual"

                edited_rows.append(row_data)
            with cols[4]:
                method_val = row.get("CategorizedBy")
                is_ai = pd.notna(method_val) and str(method_val) == "AI"
                is_manual = pd.notna(method_val) and str(method_val) == "Manual"
                if is_ai:
                    st.markdown("🤖 **AI**", unsafe_allow_html=True)
                elif is_manual:
                    st.markdown("✏️ **Manual**", unsafe_allow_html=True)
                else:
                    st.markdown("📋 **Rules**", unsafe_allow_html=True)
            with cols[5]:
                confidence = row["Confidence"]
                if confidence == "low":
                    st.markdown("⚠️", unsafe_allow_html=True)
                elif confidence == "medium":
                    st.markdown("🔍", unsafe_allow_html=True)
                else:
                    st.markdown("✅", unsafe_allow_html=True)

        edited_df = pd.DataFrame(edited_rows)
        st.session_state["edited_df"] = edited_df

        # Legend
        st.markdown("---")
        st.caption("**Legend:** ✅ High confidence (rules match) · 🔍 Medium (AI categorized) · ⚠️ Low (needs review) · ✏️ Manual override")

        # Export
        st.markdown("---")
        st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
        export_df = edited_df[["Date", "Description", "Amount", "Account", "Confidence", "CategorizedBy"]]
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Categorized Transactions (CSV)",
            data=csv_data,
            file_name="categorized_transactions.csv",
            mime="text/csv",
            use_container_width=True
        )


# =============================================================================
# TAB 3: TRIAL BALANCE
# =============================================================================

with tab_trial:
    if "data_ready" not in st.session_state or not st.session_state["data_ready"]:
        st.info("📂 Upload a CSV file in the **Upload & Map** tab first to see the trial balance.")
    else:
        # Use edited data if available, otherwise use categorized
        df_for_journal = st.session_state.get("edited_df", st.session_state["categorized_df"])
        journal_df = create_journal_entries(df_for_journal)
        trial_balance = build_trial_balance(journal_df)

        st.markdown('<div class="section-header">Trial Balance</div>', unsafe_allow_html=True)

        # Format and display
        display_tb = trial_balance.copy()
        display_tb["Debit"] = display_tb["Debit"].apply(lambda x: f"${x:,.2f}")
        display_tb["Credit"] = display_tb["Credit"].apply(lambda x: f"${x:,.2f}")
        display_tb["Balance"] = display_tb["Balance"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(display_tb, use_container_width=True, hide_index=True)

        # Balance check
        total_debits = trial_balance["Debit"].sum()
        total_credits = trial_balance["Credit"].sum()
        difference = abs(total_debits - total_credits)

        if difference < 0.01:
            st.markdown(
                f'<div class="balance-check valid">✅ Trial Balance Balances: ${total_debits:,.2f} Debits = ${total_credits:,.2f} Credits</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="balance-check invalid">❌ Trial Balance Does NOT Balance! Difference: ${difference:,.2f}</div>',
                unsafe_allow_html=True
            )


# =============================================================================
# TAB 4: PROFIT & LOSS
# =============================================================================

with tab_pnl:
    if "data_ready" not in st.session_state or not st.session_state["data_ready"]:
        st.info("📂 Upload a CSV file in the **Upload & Map** tab first to see the P&amp;L statement.")
    else:
        df_for_pnl = st.session_state.get("edited_df", st.session_state["categorized_df"])
        pnl = build_profit_and_loss(df_for_pnl)

        st.markdown('<div class="section-header">Profit &amp; Loss Statement</div>', unsafe_allow_html=True)

        # Summary metric cards
        pmcol1, pmcol2, pmcol3 = st.columns(3)
        with pmcol1:
            st.metric("Total Revenue", f"${pnl['total_revenue']:,.2f}")
        with pmcol2:
            st.metric("Total Expenses", f"${pnl['total_expenses']:,.2f}")
        with pmcol3:
            net = pnl["net_profit"]
            st.metric("Net Profit", f"${net:,.2f}", delta=f"{'Profit' if net>=0 else 'Loss'}")

        st.markdown("---")

        # Two columns: Revenue breakdown and Expense breakdown
        rcol, ecol = st.columns(2)

        with rcol:
            st.markdown("### 💰 Revenue Breakdown")
            rev_df = pd.DataFrame(
                [(acct, abs(amt)) for acct, amt in pnl["revenue"].items()],
                columns=["Account", "Amount"]
            )
            if not rev_df.empty:
                st.dataframe(
                    rev_df.style.format({"Amount": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )

                # Revenue bar chart
                st.markdown("### Revenue by Category")
                rev_chart_data = rev_df.set_index("Account")
                st.bar_chart(rev_chart_data, height=250, color="#008300")
            else:
                st.info("No revenue transactions.")

        with ecol:
            st.markdown("### 💸 Expense Breakdown")
            exp_df = pd.DataFrame(
                [(acct, abs(amt)) for acct, amt in pnl["expenses"].items()],
                columns=["Account", "Amount"]
            )
            if not exp_df.empty:
                st.dataframe(
                    exp_df.style.format({"Amount": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )

                # Expense bar chart
                st.markdown("### Expenses by Category")
                exp_chart_data = exp_df.set_index("Account")
                st.bar_chart(exp_chart_data, height=250, color="#d03b3b")
            else:
                st.info("No expense transactions.")

        st.markdown("---")

        # P&L Summary bar chart
        st.markdown("### P&amp;L Summary")
        pnl_summary = pd.DataFrame({
            "Category": ["Revenue", "Expenses", "Net Profit"],
            "Amount": [pnl["total_revenue"], -pnl["total_expenses"], pnl["net_profit"]]
        })
        pnl_bar = pnl_summary.set_index("Category")
        st.bar_chart(pnl_bar, height=300, color="#008300")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("""
<div class="footer">
    Built with Python &middot; pandas &middot; Streamlit &middot; OpenRouter AI
</div>
""", unsafe_allow_html=True)