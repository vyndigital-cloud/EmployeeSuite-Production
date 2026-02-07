# Developer Guide

## Local Development (Docker)

We use Docker to mirror the production environment exactly.

### Quick Start
1. Copy environment template:
   ```bash
   cp .env.docker .env
   ```
2. Fill in your Shopify API keys in `.env`
3. Start the environment:
   ```bash
   docker-compose up --build
   ```
4. Access app at http://localhost:5000

### Running Tests
Run the test suite inside the container:
```bash
docker-compose exec app pytest
```

To run only smoke tests (critical for deployment):
```bash
docker-compose exec app pytest -m smoke
```

---

## Deployment Workflow (CI/CD)

**Never push directly to production without testing.** The CI/CD pipeline enforces this.

### 1. Automated Tests (CI)
Every push triggers the test suite in GitHub Actions (`.github/workflows/ci.yml`).
- Runs unit + smoke tests
- Blocks if ANY test fails

### 2. Deployment (CD)
When code is pushed to `main` and passes CI:
1. Deploys to Render automatically
2. Runs **Post-Deployment Smoke Tests** against live URL
3. Checks `/` and `/auth/callback` for 500 errors

### Rollback
If the deployment fails check (returns 500):
- Use Render Dashboard to rollback to previous version immediately.

---

## Troubleshooting

### "User has no shop_url attribute"
Check you are querying `ShopifyStore` model, not `User` model.
User model has NO shop columns.

### RecursionError
Check you are using `session.get('_user_id')` and not `current_user` inside `load_user_from_request`.
