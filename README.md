# Ombudsman Response Agent

Reads an ombudsman complaint and the screenshots of the customer's records, assesses the customer's sentiment, picks the right reply template for the product and fills it with the customer's data.

**Stack:** Python · LangChain · Azure OpenAI (GPT-4o-mini) · Azure Document Intelligence · python-docx · Streamlit
**Role:** Lead developer: design and implementation
**Code status:** partial. The front end and orchestration are here; the per-product sub-agent folders (`comercializacao/`, `sinistro/`) were not available when this portfolio was assembled, so the app does not run as is.

> Built at a large Brazilian insurer. The company is replaced by the fictional **Acme Seguros**, and every name, document and data point here is fictional. Code, prompts and UI are in Portuguese, written for Brazilian business teams.

## Problem

For each complaint, the ombudsman team searched by hand for the right reply template (by line of business, product and contract type) and then copied the customer's details from several system screens into it.

## What I built

- **Inputs:** the complaint form (PDF) and the system screenshots with the customer's data (PDF).
- **Sentiment analysis** of the complaint description, to gauge how dissatisfied the customer is.
- **Template selection** from the line of business, product and contract type on the form.
- **Three-step chain per product** (global analysis → system-screen extraction → final reply), organised by line of business, for example life sales, pension claims and life claims.
- **Output:** the filled reply, plus a tab with the raw template used, so the analyst can check what the model changed.

## Run it

The missing sub-agent folders are needed before the app can start. The entry point would be:

```bash
pip install -r requirements.txt
cp .env.example .env                               # Azure OpenAI + Document Intelligence
streamlit run streamlit_app.py
```

---
Part of my [AI engineering portfolio](https://github.com/lucasboliveirasipp).
