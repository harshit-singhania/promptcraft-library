# 🧠 PromptCraft Lab

**PromptCraft Lab** is a modular **LLM Workflow Assistant Suite** designed for **AI developers, power users, and teams** building applications with Large Language Models (LLMs).  
It helps you **organize, version, test, and optimize** prompts, track **token usage & cost analytics**, and run **LLM-assisted sessions** — all through a clean, API-first backend.

---

## 🚀 Features

### 🧩 Prompt Management
- Create and version prompts with metadata (tags, default model, description).
- Reuse across projects and share with team members.
- Built-in cost and performance tracking (tokens, latency, success rate).

### 🧠 Session & Context Tracking
- Structured conversational sessions with full message history.
- Context recall — reuse prior interactions in new sessions.
- Automatic logging of user ↔ assistant exchanges.

### 📊 Usage Analytics & Cost Dashboard
- Token usage, response quality, and API cost aggregation.
- Detect abnormal token spikes and performance drops.
- Integration-ready for external observability (Grafana, Prometheus, etc).

### 🔍 Output Validation Layer *(planned)*
- Optional LLM-based self-verification or RAG-based factual checks.
- Simple “response audit hooks” to attach validation rules.

### ⚙️ Integration Hooks
- Lightweight REST API for any frontend or tool (VSCode, Jupyter, internal dashboards).
- Event hooks for async workflows (Redis-based queue ready).

---

## 🧱 Architecture

**Tech Stack:**
| Layer | Technology |
|-------|-------------|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) |
| Database | PostgreSQL (Dockerized) |
| Caching / Queue | Redis |
| Dependency & Packaging | Poetry |
| Tests | Pytest + FastAPI TestClient |
| Auth & Config | Pydantic Settings |
| Containerization | Docker & Docker Compose |

### Directory Layout
```

promptcraft-lab/
├── app/
│   ├── main.py             # FastAPI app entrypoint
│   ├── models.py           # SQLAlchemy ORM models
│   ├── schemas.py          # Pydantic models
│   ├── crud.py             # Database access layer
│   ├── db.py               # Engine and session config
│   └── config.py           # Environment settings
├── migrations/
│   └── 000_init.sql        # Schema definition (users, prompts, sessions, etc.)
├── tests/
│   └── test_api.py         # End-to-end API tests (mocked CRUD)
├── docker-compose.yml
├── pyproject.toml
└── README.md

````

---

## ⚡ Quickstart (Local Development)

### 1. Clone and setup
```bash
git clone https://github.com/harshit-singhania/promptcraft-lab.git
cd promptcraft-lab
poetry install
````

### 2. Start services

```bash
docker compose up -d db redis
```

### 3. Apply migrations

```bash
psql "postgresql://postgres:postgres@127.0.0.1:5432/llm_workflow" -f migrations/000_init.sql
```

### 4. Run API server

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit → [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ✅ Running Tests

All API routes are covered with mocked CRUD logic for isolated validation.

```bash
poetry run pytest -q
```

---

## 🧩 Example API Flow

```bash
# Create project
curl -s -X POST http://127.0.0.1:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project","description":"for testing"}' | jq

# Create prompt
curl -s -X POST http://127.0.0.1:8000/api/v1/prompts \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<project_id>","name":"Summarize","template":"Summarize: {{input}}"}' | jq

# Create session
curl -s -X POST http://127.0.0.1:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<project_id>","title":"Exploration"}' | jq
```

---

## 🌐 Roadmap

| Stage | Feature                         | Status         |
| ----- | ------------------------------- | -------------- |
| 1     | Core API with CRUD & models     | ✅ Done         |
| 2     | Token usage analytics dashboard | 🔄 In progress |
| 3     | LLM-assisted prompt grading     | 🧩 Planned     |
| 4     | Team auth & sharing             | 🧩 Planned     |
| 5     | SDK + web dashboard             | 🧩 Planned     |

---

## 🧰 For Developers

To run linters and hooks:

```bash
poetry run pre-commit run --all-files
```

To format automatically:

```bash
poetry run black .
poetry run isort .
```

---

## 🧑‍💻 Author

**Harshit Singhania**
AI Developer | Back-end Engineer | LLM Enthusiast
[GitHub](https://github.com/harshit-singhania)

---