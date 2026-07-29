# PMG360 Member Chatbot -- Demo

Standalone one-page showcase of the PMG360 member-profile widget and its chatbot. No backend,
database, or React app required -- a fixed demo member, styled with the real product's own
stylesheet (`assets/Iframe.css`, copied from the frontend) and image assets.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Requires an `ANTHROPIC_API_KEY` -- either export it in your shell, or create a local `.env` file:

```
ANTHROPIC_API_KEY="sk-ant-..."
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (already done if you're reading this there).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Pick this repo/branch, and set the main file path to `app.py`.
4. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Deploy.
