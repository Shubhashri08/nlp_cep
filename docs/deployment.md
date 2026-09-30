# Security, Privacy, and Docker Deployment

## 1. Security & Privacy Architecture (`docs/security.md`)
- **Authentication**: JWT HS256 tokens with configurable expiration (1440 min) and bcrypt password hashing (work factor 12).
- **Role-Based Access Control (RBAC)**:
  - `ADMIN`: User management, dataset uploads, system configuration.
  - `PLANNER`: Scenario creation, recommendations, spatial analysis.
  - `ANALYST`: Model evaluation, GIS inspection, ML registry.
  - `VIEWER`: Read-only access to dashboards and maps.
- **PII Minimization**: Citizen grievance submission does not expose phone numbers or personal emails in public analytics APIs.
- **Immutable Audit Logging**: Every login, model inference, dataset modification, and scenario creation is recorded with user ID, action, resource type, and timestamp.

## 2. Deployment & Execution Guide (`docs/deployment.md`)

### Local Setup & Execution
```bash
# 1. Start Python backend
source venv/bin/activate
PYTHONPATH=. python scripts/seed_real_data.py
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. In another terminal, start React frontend
cd frontend
npm install
npm run dev
```

### Production Build
To create a production bundle for the frontend:
```bash
cd frontend
npm run build
```
The optimized bundle will be created in `frontend/dist/`.

