# Muelsyse-CI

A modern, self-hosted CI/CD system with GitHub Actions compatible configuration.

> Named after Muelsyse (缪尔赛思), a Rhine Lab operator from Arknights.

## Features

- **GitHub Actions Compatible** - Use familiar YAML syntax for pipeline configuration
- **Self-hosted & SaaS** - Deploy on your own infrastructure or use as a service
- **Multi-tenant** - Built-in tenant isolation for enterprise deployments
- **Docker & Shell Executors** - Run jobs in containers or directly on hosts
- **Real-time Logs** - WebSocket-based live log streaming
- **Matrix Builds** - Parallel builds across multiple configurations
- **Secrets Management** - Encrypted storage for sensitive data
- **Artifacts** - Upload and share build outputs between jobs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web UI (Vue3)                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Control Plane (Django)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  REST API    │  │  WebSocket   │  │  Celery Scheduler    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐
│   PostgreSQL    │  │     Redis       │  │   Runner Pool        │
│   (Storage)     │  │  (Cache/Queue)  │  │   (Rust Executors)   │
└─────────────────┘  └─────────────────┘  └──────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Control Plane | Python Django + DRF + Channels |
| Web UI | Vue3+MDUI |
| Runner | Rust + Tokio |
| Database | PostgreSQL |
| Cache/Queue | Redis + Celery |
| WebSocket | Django`` Channels |

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourorg/muelsyse-ci.git
cd muelsyse-ci

# Create environment file
cp control-plane/Python-src/.env.example .env
# Edit .env with your settings

# Start all services
docker-compose up -d

# Access the UI at http://localhost:3000
```

### Manual Setup

#### Control Plane

```bash
cd control-plane/Python-src

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/development.txt

# Set up database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

#### Runner

```bash
cd runners

# Build
cargo build --release

# Configure
cp runner.toml.example runner.toml
# Edit runner.toml with your settings

# Run
./target/release/muelsyse-runner
```

## Pipeline Configuration

Create `.muelsyse/pipeline.yml` in your repository:

```yaml
name: Build and Test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: [linux, docker]
    container:
      image: node:20
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test

  build:
    runs-on: [linux]
    needs: [test]
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

## API Documentation

Access the Swagger UI at `/api/docs/` when running the control plane.

## Project Structure

```
muelsyse-ci/
├── control-plane/
│   ├── Muelsyse-Web-UI/     # React frontend
│   └── Python-src/          # Django backend
│       ├── apps/
│       │   ├── core/        # Core utilities
│       │   ├── tenants/     # Multi-tenancy
│       │   ├── auth_service/# Authentication
│       │   ├── pipelines/   # Pipeline management
│       │   ├── executions/  # Execution tracking
│       │   ├── runners/     # Runner management
│       │   ├── logs/        # Log storage
│       │   ├── secrets/     # Secret management
│       │   └── artifacts/   # Build artifacts
│       └── muelsyse/        # Django project config
├── runners/                  # Rust runner
│   └── src/
│       ├── executor/        # Docker/Shell executors
│       ├── client/          # Control plane client
│       └── job/             # Job execution
├── yaml/                     # Example configurations
└── docker-compose.yml        # Docker deployment
```

## License

GNU GPL

## ToolChain

Develop：[Logos](https://github.com/Zixiao-System/logos)


