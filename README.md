---
title: ALFRED Meta-Agent
emoji: 🎩
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.32.0
app_file: main.py
pinned: false
---

# 🎩 ALFRED: Meta-Agent Orchestrator

**ALFRED** (Advanced Logical Functional Retrieval & Execution Director) is a multi-agent orchestrator built with **LangGraph**, **Streamlit**, and **Docker**. It uses a specialized director-worker architecture to delegate complex tasks across specialized AI personas, interacting seamlessly with databases, web portals, security tools, and financial APIs.

---

## 🧠 Architecture & Agents

ALFRED operates as the core director, interpreting user intent and routing tasks to dedicated sub-agents.

- **🎩 ALFRED (Director):** The core orchestrator. Evaluates the state and decides who should work next. Powered by Google Gemini (1.5-pro).
- **🛡️ AFANDE (Security & Systems):** Handles remote portal document scraping via OpenClaw API, Nmap security audits, system shell executions, and file operations.
- **📊 DATA_ANALYST (Data & Finance):** Specializes in data science, math, financial calculations (e.g., RSI via yfinance), DuckDB workflows, and text database saving.
- **🎨 CONTENT_CREATOR (Creative Media):** Synthesizes data into visual formats including charts, PDF reports, AI videos, and audio transcription.
- **🎓 STUDENT (Academic Orchestrator):** Coordinates portal scraping tasks, manages 'allowed-access-accounts', and oversees document submissions.

### 🎭 Dynamic Personas

ALFRED can adopt different operational modes via the UI to tailor his workflows:

- **Student:** Syllabus parsing, assignment workflow management, and deadline compliance.
- **Content Creator:** Digital audience acquisition, media synthesis delegation, and n8n workflow orchestration.
- **Business Analyst:** Profitability optimization, CAC calculation, and Tableau data preparation.
- **Data Scientist:** Predictive modeling, statistical testing, and DuckDB/PostgreSQL interaction.
- **Ethical Hacker:** Defensive asset protection and containerized sandbox scanning.

---

## 🚀 Features

- **LangGraph State Routing:** Complex conditional edge routing ensuring tasks stay within their designated agent boundaries.
- **Interactive Streamlit UI:** A responsive chat interface with a dedicated sidebar for persona swapping.
- **Multimodal Vision:** ALFRED can take snapshots of your local screen and analyze them via multimodal payloads.
- **Containerized Infrastructure:** Seamless deployment using Docker Compose, integrating a local PostgreSQL warehouse (`alfred_warehouse`) and Adminer UI.
- **Headless Browser Delegation:** Web tasks are routed through the isolated **OpenClaw API** for safe, containerized web execution.
- **Ngrok Auto-Tunneling:** Pre-configured Docker service exposes your backend securely for Hugging Face Spaces and remote access.
- **Dynamic Task Scheduling:** Pause, edit, resume, and track scheduled cron jobs natively within Streamlit.
- **Live Capabilities Dashboard:** Dynamically view and update ALFRED's capabilities catalog directly from the Streamlit UI.
- **Local Inference Engine Support:** Seamlessly connect ALFRED to a local LLM (like Ollama or LM Studio) to save on API costs and maximize privacy.

---

## 🛠️ Prerequisites

- Docker Desktop or Docker Engine & Docker Compose
- Python 3.10+ (if running locally without Docker)
- Required API Keys:
  - Google Gemini API Key (`GOOGLE_API_KEY`)
  - OpenAI API Key (`OPENAI_API_KEY`)
  - Groq API Key (`GROQ_API_KEY`)

---

## ⚙️ Setup and Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/ALFRED.git
   cd ALFRED
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your credentials:

   ```env
   GOOGLE_API_KEY=your_gemini_key
   OPENAI_API_KEY=your_openai_key
   GROQ_API_KEY=your_groq_key

   # Student Portal Tool Config
   STUDENT_PORTAL_USER=your_username
   STUDENT_PORTAL_PASS=your_password

   # OpenClaw Connection
   OPENCLAW_API_URL=http://openclaw:8000/api/automate

   # Ngrok (Required for external/Hugging Face webhooks)
   NGROK_AUTHTOKEN=your_ngrok_token_here
   ```

3. **Run with Docker Compose:**
   Boot up the ALFRED orchestrator, the PostgreSQL database, and Adminer UI:

   ```bash
   docker-compose up -d --build
   ```

4. **Access the Application:**
   - **ALFRED Command Center:** http://localhost:8501
   - **Database Admin UI:** http://localhost:8080

---

## ☁️ Deploying to Hugging Face Spaces

ALFRED is pre-configured with YAML frontmatter to be instantly deployed as a **Hugging Face Space**.

1. Create a new Space on Hugging Face and choose the **Streamlit** SDK.
2. Push this repository directly to your Space.
3. Add your environment variables (like `OPENCLAW_API_URL` and `DATABASE_URL`) to your Space's **Secrets** settings. _Note: Use an ngrok URL to bridge the cloud Space back to your local machine!_

## 🧠 Connecting a Local Inference Engine

You can run ALFRED using entirely local, free, and private models (e.g., via **Ollama**, **LM Studio**, or **vLLM**) instead of Gemini.

1. Start your local inference engine with an OpenAI-compatible server (e.g., LM Studio on port `1234`).
2. Use ngrok to expose your local LLM to the internet (if ALFRED is hosted on Hugging Face): `ngrok http 1234`
3. Update your `.env` (or Hugging Face Space Secrets) with the tunnel credentials:
   ```env
   LOCAL_INFERENCE_URL=https://your-ngrok-url.app/v1
   LOCAL_MODEL_NAME=your-local-model-name
   LOCAL_INFERENCE_KEY=not-needed
   ```
   ALFRED will automatically detect the `LOCAL_INFERENCE_URL` and reroute all AI processing to your local GPU!

---

## 📂 Project Structure

```text
ALFRED/
├── agents/                 # Logic for sub-agents (AFANDE, MOR, SHUGA)
├── config/                 # Configuration files (system_prompts.py)
├── scripts/                # Master workflows, logics, and automated SOPs
├── tools/                  # Extensible capabilities (finance, security, creative)
├── data/                   # Local staging area for downloads and DuckDB
├── graph.py                # Core LangGraph orchestration and routing logic
├── main.py                 # Streamlit graphical interface
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Container definition for ALFRED Core
└── requirements.txt        # Python dependencies
```

=======
title: ALFRED
emoji: 🚀
colorFrom: red
colorTo: red
sdk: docker
app_port: 8501
tags:

- streamlit
  pinned: false
  short_description: Advanced logistics functional retrival execution director
  license: apache-2.0

---

# Welcome to Streamlit!

Edit `/src/streamlit_app.py` to customize this app to your heart's desire. :heart:

If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).

> > > > > > > 8b8b8520342f5ec181abe49a0e8ef312a183bbe5
