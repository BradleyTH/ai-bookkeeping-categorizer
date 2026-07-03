# AI Bookkeeping Categorizer

A tool that takes a CSV of bank transactions, sorts each one into the right accounting category, applies double entry bookkeeping, and produces a trial balance and a profit and loss statement. It leans on AI for the transactions that plain keyword rules can't figure out on their own.

I built this as an accounting student who wanted to see for myself where AI actually fits into a real bookkeeping workflow, and where it doesn't. The interesting part turned out to be the boundary between the two. Rules handle the obvious transactions, AI handles the ambiguous ones, and a person stays in the loop for anything the AI isn't confident about.

(Add a screenshot or a short GIF of the app here. It makes a big difference to how the project comes across.)

Live app: add your Streamlit Cloud link here

Demo: upload the included sample_transactions.csv to try it without any data of your own.

## What problem it solves

Categorizing bank transactions by hand is slow and repetitive, and it's one of the least enjoyable parts of bookkeeping. Most transactions are predictable, so "UBER" is travel and "AWS" is software, but plenty of them are vague enough that a simple keyword list just gives up. This tool automates the predictable ones with rules, sends the rest to an AI model to classify, and flags anything the AI wasn't sure about so a person can check it. Then it turns the categorized data into proper double entry records and financial statements.

## How it works

The pipeline runs in a few stages.

First it loads a CSV of transactions with a date, a description, and an amount. There's a column mapping step so it can handle real bank exports whose columns are named differently, plus a cleanup path for messier files.

Next it categorizes with rules. A keyword matcher assigns the obvious transactions, like "WOOLWORTHS", "SALARY PAYMENT", or "GOOGLE ADS", to their accounts. This part is fast, free, and predictable.

Then it categorizes with AI. Anything the rules leave as uncategorized gets sent to an AI model through OpenRouter, which reads the description, picks an account from the chart of accounts, and returns a confidence level. Low confidence results get flagged for review instead of being trusted blindly.

After that it applies double entry. Every transaction becomes a debit and a matching credit, with the bank account always on one side. Money going out debits an expense and credits the bank, and money coming in debits the bank and credits revenue.

Finally it builds the reports. There's a trial balance, which checks that total debits equal total credits, and a simple profit and loss statement.

Every transaction is also tagged with how it was categorized, whether by Rules, AI, or a Manual override, so you can always see where a classification came from. That kind of transparency matters in accounting, where you often have to justify a number.

## The accounting side

The whole thing is built on a chart of accounts grouped by type, covering revenue, expenses, and the bank asset, and on double entry rules where every entry has an equal debit and credit. The trial balance is the built in integrity check. If debits don't equal credits, something has gone wrong, and the tool says so.

A couple of design decisions are worth explaining.

It's a profit and loss tool, not a full ledger. It produces an income statement rather than a balance sheet, so the chart of accounts sticks to revenue and expense accounts. Adding asset, liability, and equity accounts only becomes meaningful once you also have a balance sheet, and a balance sheet needs opening balances that bank data alone doesn't give you. Rather than build that halfway, I left it as a future step, noted below.

Rules also encode judgment. Supermarket spending, for example, shouldn't automatically land in "Meals and Entertainment", because in a business context that account is for client meals, not groceries. Small decisions like that are where accounting knowledge actually shows up, and getting them wrong quietly distorts the profit and loss.

## Tech

It's written in Python, using pandas for the data handling and the accounting logic. The AI categorization goes through the OpenRouter API and is model agnostic, so you pick which model to use with an environment variable. The web interface is built with Streamlit.

The AI layer is built to keep working even when things go wrong. If the API is unavailable or returns something it can't parse, it falls back to a simple guess based on the amount, treating money in as income and money out as expense, so you still get usable output instead of a crash.

## Running it locally

Install the dependencies.

```
pip install -r requirements.txt
```

Set your OpenRouter API key. Never hard code it into the file.

```
setx OPENROUTER_API_KEY "your-key-here"
```

Run the web app.

```
streamlit run app.py
```

Then upload a CSV, or the included sample_transactions.csv, and map the columns if you need to.

The expected CSV format looks like this, though you can also map your own columns to these fields inside the app.

```
Date,Description,Amount
2024-01-01,STRIPE PAYOUT,2500.00
2024-01-04,UBER EATS,-18.75
```

Positive amounts are money coming in, and negative amounts are money going out.

## A note on the data

All of the sample data is made up. Don't upload real bank statements to a public deployment; use dummy data instead. If you do run it on your own transactions locally, remember that the categorizations, especially the AI ones, are suggestions to review rather than final answers.

## What I'd add next

A balance sheet would be the natural next step, and it would justify adding asset, liability, and equity accounts properly.

Transfers deserve better handling too, since moving money between your own accounts isn't really income or expense and shouldn't be treated as either.

The import side could also be smarter about the full range of bank export quirks, like unusual date formats, separate debit and credit columns, running balance columns, and double encoded files. I ran into several of these along the way, and each one was a reminder that real financial data is a lot messier than any tidy sample.

## An honest note

I built this with AI assistance for the coding. The accounting design is mine. The chart of accounts, the double entry logic, the split between rules and AI, and the choice to keep a person in the loop for low confidence categorizations all came from what I've been studying, and I'm happy to walk through any part of it.
