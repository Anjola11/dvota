# Dvota API

**Dvota** is a secure, transparent, and accessible digital voting platform. This backend API, built with FastAPI, manages user authentication, election creation, and the voting process using a robust stack including SQLModel, Redis, and Brevo for transactional emails.

## 🚀 Features

### 🔐 Authentication & User Management

* **Secure Signup & Login**: Implements JWT-based authentication with password hashing via `bcrypt`.
* **OTP Verification**: Multi-stage verification for signups and password resets using 6-digit codes.
* **Transactional Emails**: Automated emails for OTP delivery and welcome messages powered by the Brevo API.
* **Token Management**: Support for access token renewal and secure logout with a token blocklist.

### 🗳️ Election Management

* **Election Lifecycle**: Creators can define elections with specific start and end times.
* **Granular Structure**: Support for adding multiple positions (e.g., President, Secretary) and candidates within an election.
* **Voter Access Control**: Ability to specify "Allowed Voters" for private or restricted elections.

### 🗳️ Voting System

* **Secure Voting**: Users can cast votes for candidates in specific positions.
* **Integrity Constraints**: Built-in database constraints to prevent duplicate voting (one vote per user per position).
* **Real-time Results**: Fetch election results and individual user ballots.

---

## 🛠️ Tech Stack

* **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
* **Database (ORM)**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
* **Database (Engine)**: PostgreSQL (via `asyncpg`)
* **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
* **Caching/Sessions**: [Redis](https://redis.io/)
* **Email Service**: [Brevo](https://www.brevo.com/)
* **Package Manager**: [uv](https://github.com/astral-sh/uv)

---

## 📋 Prerequisites

* **Python**: >= 3.13
* **PostgreSQL**: A running instance for persistent data storage.
* **Redis**: For token blacklisting and session management.
* **Brevo API Key**: Required for sending OTP and welcome emails.

---

## ⚙️ Configuration

The application uses Pydantic-settings to manage configuration via environment variables or a `.env` file. Create a `.env` file in the root directory with the following keys:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dvota
BREVO_API_KEY=your_brevo_api_key
BREVO_EMAIL=your_sender_email
BREVO_SENDER_NAME=Dvota
JWT_KEY=your_secret_jwt_key
JWT_ALGORITHM=HS256
REDIS_HOST=localhost
REDIS_PORT=6379

```

---

## 📂 Project Structure

```text
dvota/
├── alembic/              # Database migration scripts
├── src/
│   ├── auth/             # User authentication (Routes, Models, Services)
│   ├── db/               # Database connections (Postgres & Redis)
│   ├── elections/        # Election & Voting logic
│   ├── emailServices/    # Brevo integration & Email templates
│   ├── templates/        # HTML email templates (Jinja2)
│   ├── utils/            # Shared utilities (OTP, Auth helpers)
│   ├── config.py         # App configuration & env loading
│   └── __init__.py       # FastAPI app initialization & Middleware
├── main.py               # Entry point (Development)
└── pyproject.toml        # Project dependencies

```

---

## 🚦 Getting Started

1. **Install Dependencies**:
```bash
uv sync

```


2. **Run Migrations**:
```bash
alembic upgrade head

```


3. **Start the Server**:
```bash
uvicorn src.__init__:app --reload

```


4. **API Documentation**:
Once the server is running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

