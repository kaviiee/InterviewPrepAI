# 🤖 InterviewPrepAI

> An AI-powered career coaching and interview preparation assistant that analyzes your resume and job description to deliver personalized guidance, gap analysis, and mock interview questions — all in real time.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture](#️-architecture)
  - [Local Architecture](#local-architecture)
  - [Production AWS Architecture](#production-aws-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Local Setup](#-local-setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Docker Setup](#-docker-setup)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Future Improvements](#-future-improvements)

---

## 🔍 Overview

**InterviewPrepAI** is a full-stack RAG (Retrieval-Augmented Generation) application that acts as a personal AI career coach. Users upload their resume (PDF) and a job description (text), and the assistant uses semantic search over those documents to answer questions, generate mock interview questions, identify skill gaps, evaluate project relevance, and provide career advice — all streamed in real time.

---

## 🏗️ Architecture

### Local Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│              Next.js 16 + React 19 (Port 3000)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / Streaming (SSE)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)               │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  /upload    │    │   /chat      │    │  /session     │  │
│  │  resume     │    │  (stream)    │    │  /reset       │  │
│  │  job        │    │              │    │  /status      │  │
│  └──────┬──────┘    └──────┬───────┘    └───────────────┘  │
│         │                  │                                │
│         ▼                  ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  RAG Pipeline                        │   │
│  │                                                     │   │
│  │  Document Loader → Text Splitter → HuggingFace      │   │
│  │  Embeddings → FAISS Vector Store → MMR Retriever    │   │
│  │  → Gemini 2.5 Flash (via OpenRouter) → Stream       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Production AWS Architecture

```
                              INTERNET
                                  |
                                  |
                                  v

                         +----------------+
                         |   Route 53     |
                         |  DNS Service   |
                         +----------------+

                                  |
                                  |
                                  v


                         +----------------+
                         |  CloudFront    |
                         | CDN + HTTPS    |
                         +----------------+

                                  |
                 ---------------------------------
                 |                               |
                 v                               v


        +----------------+             +----------------+
        | Next.js App    |             | API Requests   |
        |                |             | /api/*         |
        | Vercel / EC2   |             +----------------+
        +----------------+                       |
                                                 |
                                                 v


                                      +----------------------+
                                      |       Nginx          |
                                      | Reverse Proxy        |
                                      | SSL Termination      |
                                      +----------------------+

                                                 |
                                                 |
                                                 v


                                      +----------------------+
                                      |        EC2           |
                                      |                      |
                                      | Docker Host          |
                                      +----------------------+

                                                 |
                          ------------------------------------------------
                          |                                              |
                          v                                              v


              +----------------------+                    +----------------------+
              | FastAPI Container    |                    | Background Workers   |
              |                      |                    | (Future)             |
              | Python               |                    | Celery               |
              | RAG Pipeline         |                    +----------------------+
              +----------------------+


                          |
        ------------------------------------------------
        |                      |                       |
        v                      v                       v


+---------------+     +----------------+       +----------------+
| Amazon S3     |     | FAISS Storage  |       | OpenRouter API |
|               |     |                |       | Gemini LLM     |
| PDFs          |     | Vector Index   |       |                |
| Documents     |     |                |       |                |
+---------------+     +----------------+       +----------------+


                          |
                          v


                +----------------------+
                | CloudWatch           |
                | Logs + Monitoring    |
                +----------------------+
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Resume Upload** | Upload your resume as a PDF; it's parsed, chunked, and indexed into a FAISS vector store |
| 📝 **Job Description Upload** | Paste or upload a job description as plain text for contextual comparison |
| 💬 **Streaming AI Chat** | Real-time token-by-token streaming responses from Gemini 2.5 Flash via OpenRouter |
| 🔍 **RAG-Powered Answers** | MMR (Maximal Marginal Relevance) retrieval ensures diverse, relevant context is passed to the LLM |
| 🎯 **Skill Gap Analysis** | Ask the AI to compare your resume against the job description and identify missing skills |
| 🧪 **Mock Interview Questions** | Generate realistic, role-specific interview questions tailored to your background |
| 🗂️ **Project Evaluation** | Ask which of your projects best fits the target role, with justification |
| 🔄 **Session Management** | Each user gets a unique UUID session; documents and chat history are isolated per session |
| 💾 **Session Persistence** | Session ID stored in `localStorage`; uploaded documents are restored on page reload |
| 🗑️ **Session Reset** | Clear all uploaded documents and chat history with a single reset call |
| 📱 **Responsive UI** | Clean, modern chat interface built with Tailwind CSS and rendered Markdown responses |

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.12 | Core runtime |
| **FastAPI** | Latest | REST API framework with async support |
| **Uvicorn** | Latest | ASGI server |
| **LangChain** | Latest | RAG orchestration framework |
| **FAISS** | Latest | In-memory vector similarity search |
| **HuggingFace Embeddings** | `all-MiniLM-L6-v2` | Sentence embedding model (384-dim) |
| **PyPDFLoader** | Latest | PDF document parsing |
| **TextLoader** | Latest | Plain text document loading |
| **RecursiveCharacterTextSplitter** | Latest | Chunk size: 1800, overlap: 400 |
| **ChatOpenAI (OpenRouter)** | Latest | LLM client pointed at OpenRouter |
| **Google Gemini 2.5 Flash** | Latest | LLM for answer generation (via OpenRouter) |
| **python-dotenv** | Latest | Environment variable management |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 16.2.9 | React framework with SSR/SSG |
| **React** | 19.2.4 | UI component library |
| **TypeScript** | ^5 | Type safety |
| **Tailwind CSS** | ^4 | Utility-first styling |
| **react-markdown** | ^10.1.0 | Render LLM Markdown responses |
| **remark-gfm** | ^4.0.1 | GitHub Flavored Markdown support |
| **@tailwindcss/typography** | ^0.5.20 | Prose styling for Markdown output |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker** | Containerization of both services |
| **Docker Compose** | Local multi-container orchestration |
| **Node.js 20 Alpine** | Lightweight frontend container base |
| **Python 3.12 Slim** | Lightweight backend container base |

---

## 📁 Project Structure

```
InterviewPrepAI/
│
├── docker-compose.yml          # Multi-container orchestration
├── README.md                   # This file
│
├── backend/
│   ├── dockerfile              # Python 3.12-slim container
│   ├── main.py                 # FastAPI app, route definitions
│   ├── rag.py                  # RAG pipeline: loading, embedding, retrieval, LLM
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables (not committed)
│   └── uploads/                # Uploaded resumes and job descriptions
│       └── <session_id>_resume.pdf
│       └── <session_id>_job.txt
│
└── frontend/
    ├── dockerfile              # Node 20-alpine container
    ├── package.json            # Node dependencies
    ├── next.config.ts          # Next.js configuration
    ├── tsconfig.json           # TypeScript configuration
    ├── eslint.config.mjs       # ESLint configuration
    ├── postcss.config.mjs      # PostCSS/Tailwind configuration
    └── app/
        ├── globals.css         # Global Tailwind styles
        ├── layout.tsx          # Root layout component
        └── page.tsx            # Main chat UI component
```

---

## 🚀 Local Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- An [OpenRouter](https://openrouter.ai/) API key with access to `google/gemini-2.5-flash`

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/InterviewPrepAI.git
   cd InterviewPrepAI
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS / Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Create the environment file**
   ```bash
   # backend/.env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

5. **Run the backend server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available at `http://localhost:8000`.  
   Interactive docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Create the environment file** *(optional — defaults to localhost:8000)*
   ```bash
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```
   The app will be available at `http://localhost:3000`.

---

## 🐳 Docker Setup

The easiest way to run the full stack locally is with Docker Compose.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Steps

1. **Create the backend environment file**
   ```bash
   # backend/.env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

2. **Build and start all containers**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

4. **Stop all containers**
   ```bash
   docker-compose down
   ```

### Docker Services

| Service | Base Image | Port | Description |
|---|---|---|---|
| `backend` | `python:3.12-slim` | `8000` | FastAPI + RAG pipeline |
| `frontend` | `node:20-alpine` | `3000` | Next.js chat UI |

> **Note:** The `uploads/` directory is mounted as a volume so uploaded documents persist across container restarts.

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ Yes | API key from [openrouter.ai](https://openrouter.ai) used to call Gemini 2.5 Flash |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | ❌ No | `http://localhost:8000` | Base URL of the FastAPI backend |

---

## 📡 API Documentation

The FastAPI backend auto-generates interactive documentation at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).

### Endpoints

---

#### `GET /session`
Creates a new unique session.

**Response**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### `GET /session/status/{session_id}`
Returns the upload status for an existing session. Used to restore state on page reload.

**Path Parameters**
| Parameter | Type | Description |
|---|---|---|
| `session_id` | `string` | UUID of the session |

**Response**
```json
{
  "resume": "550e8400-e29b-41d4-a716-446655440000_resume.pdf",
  "job_uploaded": true
}
```

---

#### `POST /upload/resume`
Uploads a resume PDF and indexes it into the session's FAISS vector store.

**Query Parameters**
| Parameter | Type | Description |
|---|---|---|
| `session_id` | `string` | UUID of the session |

**Form Data**
| Field | Type | Description |
|---|---|---|
| `file` | `File` | Resume PDF file |

**Response**
```json
{
  "message": "Resume uploaded successfully"
}
```

---

#### `POST /upload/job`
Uploads a job description as plain text and adds it to the session's vector store.

**Query Parameters**
| Parameter | Type | Description |
|---|---|---|
| `session_id` | `string` | UUID of the session |

**Form Data**
| Field | Type | Description |
|---|---|---|
| `file` | `File` | Job description `.txt` file |

**Response**
```json
{
  "message": "Job description uploaded successfully"
}
```

---

#### `POST /chat`
Sends a message and streams back the AI response token by token.

**Request Body**
```json
{
  "message": "What are my strongest skills for this role?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**  
`Content-Type: text/plain` — chunked streaming response.  
The response is streamed token by token from Gemini 2.5 Flash. The last 5 turns of conversation history are included in each prompt for context continuity.

---

#### `POST /reset`
Clears all documents, the vector store, and chat history for a session.

**Query Parameters**
| Parameter | Type | Description |
|---|---|---|
| `session_id` | `string` | UUID of the session |

**Response**
```json
{
  "message": "Session reset"
}
```

---

### RAG Pipeline Details

```
User Query
    │
    ▼
FAISS MMR Retriever
(k=10 docs, fetch_k=30 candidates)
    │
    ▼
Top-k Document Chunks
(from resume + job description)
    │
    ▼
Prompt Assembly
(system prompt + last 5 history turns + context chunks + query)
    │
    ▼
Gemini 2.5 Flash via OpenRouter
(temperature=0, streaming=True)
    │
    ▼
Streamed Response Tokens → Client
```

**Chunking Strategy**
- Chunk size: **1800 characters**
- Chunk overlap: **400 characters**
- Splitter: `RecursiveCharacterTextSplitter`

**Embedding Model**
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimensions: 384
- Provider: HuggingFace (runs locally, no API key needed)

---

## 🔮 Future Improvements

| Improvement | Description |
|---|---|
| ☁️ **Amazon S3 Document Storage** | Replace local `uploads/` directory with S3 for persistent, scalable document storage in production |
| 🔄 **Celery Background Workers** | Offload document processing and vector index building to async Celery tasks to avoid blocking API responses |
| 💾 **Persistent Vector Store** | Persist FAISS indexes to disk (or migrate to Pinecone/Weaviate/pgvector) so sessions survive server restarts |
| 🔐 **User Authentication** | Add JWT-based auth (AWS Cognito or Auth.js) so users can maintain long-term profiles and history |
| 🗃️ **Database-Backed Chat History** | Store conversation history in PostgreSQL/DynamoDB instead of in-memory `defaultdict` |
| 📊 **Analytics Dashboard** | Track usage patterns, popular question types, and session metrics via CloudWatch or a custom dashboard |
| 🎤 **Voice Input** | Add speech-to-text support so users can practice speaking answers aloud |
| 📄 **Multi-Document Support** | Allow uploading multiple resumes or multiple job descriptions and comparing across them |
| 🧠 **Fine-Tuned Embeddings** | Fine-tune the embedding model on career/HR domain data for higher retrieval precision |
| 🌐 **Nginx + SSL** | Add Nginx reverse proxy with Let's Encrypt SSL certificates for production EC2 deployment |
| 📧 **Report Export** | Generate and download a PDF summary report of skill gaps, suggested projects, and prep tips |
| 🔁 **Interview Simulation Mode** | A dedicated mode that simulates a full mock interview with follow-up questions and scoring |

---

## 📄 License

This project is licensed under the terms of the [LICENSE](./LICENSE) file included in the repository.

---

<div align="center">
  <sub>Built with ❤️ using FastAPI, LangChain, FAISS, Gemini, and Next.js</sub>
</div>
