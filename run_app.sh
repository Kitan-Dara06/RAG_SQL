#!/bin/bash
# Start the Streamlit UI

echo "🚀 Starting SQL_RAG Streamlit UI..."
./venv/bin/streamlit run src/ui/streamlit_app.py --server.headless=false --server.port=8501
