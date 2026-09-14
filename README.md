# 🌾 KrishiRAG — Farmer Query Advisory & Live Mandi Intelligence

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat&logo=react)](https://reactjs.org/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20API-orange?style=flat)](https://groq.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Search-FAISS-blue?style=flat)](https://github.com/facebookresearch/faiss)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)

**KrishiRAG** is an AI-powered agricultural advisory system designed for farmers in Punjab. It combines a retrieve-and-rerank RAG (Retrieval-Augmented Generation) pipeline grounded in official **Punjab Agricultural University (PAU)** Package of Practices guides with real-time **Mandi commodity market price lookups**.

---

## 🌐 Live Deployments

- **🎨 Frontend Application**: [https://krishirag.vercel.app](https://krishirag.vercel.app)
- **⚡ Backend REST / SSE API**: [https://krishirag-backend.onrender.com](https://krishirag-backend.onrender.com)

---

## 🌟 Key Features

- **🌾 Grounded & Cited Crop Advisories**: Provides natural, farmer-friendly answers for sowing times, seed rates, pest management, herbicides, and crop varieties — citing specific PAU advisory files and page numbers.
- **⚡ SSE Word-by-Word Streaming**: Delivers a continuous, human-like typewriter streaming response using Server-Sent Events (SSE) and an animated typing cursor.
- **💬 Natural Conversational Intelligence**: Warm agricultural advisor persona that naturally greets farmers, chats casually, answers technical farming questions, and politely redirects out-of-scope general trivia.
- **📊 Real-Time Mandi Price Intelligence**: Connects to Neon PostgreSQL to query and filter live market commodity rates across states, districts, and crops.
- **🎯 Two-Stage Retrieval & Reranking**: Combines fast Bi-Encoder vector search (`sentence-transformers/all-MiniLM-L6-v2`) with a heavy Cross-Encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for top relevance accuracy.

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Farmer Query] --> B[FastAPI Backend /api/query/stream]
    B --> C[Bi-Encoder Query Vectorization]
    C --> D[FAISS Dense Index Search - Top 10 Chunks]
    D --> E[CrossEncoder Reranker - Top 3 Chunks]
    E --> F[Grounded Prompt Construction]
    F --> G[Groq LLM Synthesis - qwen/qwen3.8-27b]
    G --> H[Server-Sent Events Stream]
    H --> I[React Typewriter Chat Interface]
```

---

## 📂 Project Structure

```
KRISHIRAG/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server (Endpoints: /api/query, /api/query/stream, /api/mandi-prices)
│   │   ├── models.py            # Pydantic request/response validation schemas
│   │   └── logging_config.py    # Query event & error logger
│   └── rag/
│       └── generator.py         # Retrieval, reranking & Groq LLM streaming module
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx       # Typewriter chat UI with sources & latencies
│   │   │   └── MandiPriceWidget.jsx # Live market rates filter & table
│   │   ├── api/client.js        # SSE streaming & API fetch client
│   │   ├── App.jsx              # Main layout dashboard
│   │   └── index.css            # Custom CSS & Tailwind setup
│   ├── package.json
│   └── vite.config.js
├── data_pipeline/
│   ├── chunk_advisories.py      # PDF parsing & text chunking
│   ├── embed_and_index.py       # Sentence-transformer embeddings & FAISS index creation
│   ├── ingest_mandi_prices.py   # Raw mandi CSV data cleaner
│   ├── load_to_postgres.py      # Database loader for Neon PostgreSQL
│   ├── scheduler.py             # Mandi price sync scheduler
│   └── test_retrieval_queries.py# Retrieval verification script
├── data/
│   └── advisories/              # PAU Package of Practices (pp_kharif.pdf, pp_rabi.pdf)
├── .env.example                 # Environment variables template
├── schema.sql                   # Mandi prices database schema
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `3.10` or higher
- **Node.js**: `v18` or higher
- **Groq API Key**: Get a free API key at [Groq Console](https://console.groq.com/)
- **Neon PostgreSQL DB**: Required for live mandi prices

---

### 🛠️ Backend Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shreyaaaah/krishirag.git
   cd krishirag
   ```

2. **Set up virtual environment & install Python dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env`*:
   ```env
   NEON_DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   GROQ_API_KEY=gsk_your_groq_api_key_here
   GROQ_MODEL=qwen/qwen3.8-27b
   ```

4. **Run the FastAPI server**:
   ```bash
   python backend/app/main.py
   ```
   *Server will run at `http://localhost:8000`*

---

### 🎨 Frontend Setup

1. **Navigate to the frontend directory & install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Vite development server**:
   ```bash
   npm run dev
   ```
   *Interface will open at `http://localhost:5173`*

---

## 💡 Example Advisory Queries

- **Wheat Sowing**: `"When should I sow wheat in Punjab?"`
- **Herbicide Doses**: `"What is the dose of sulfosulfuron for wheat?"`
- **Pest Control**: `"How do I control whitefly in cotton?"`
- **Weed Management**: `"Phalaris minor control in wheat"`

---

## 📄 License

Distributed under the MIT License. Grounded agricultural data sourced from Punjab Agricultural University (PAU) Package of Practices guides.
