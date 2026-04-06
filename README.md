# backloggd replica

## Quick Start

### 1. Run services 

```bash
docker compose up -d
```

### 2. Install deps 

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. `.env`

Copy `.env.example`  to `.env`

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start the app 

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing 

Recommend testing the application using Swagger docs, also run `localhost:8025` to view sent emails in Mailhog.
You can use Postman as well, collection in json format is present in project, however needs additional setup for authentication.

To interact with `elasticsearch`, you can use the following command:

- To see all logs
```bash
curl "localhost:9200/game-backlog-logs/_search?pretty" \
  -H 'Content-Type: application/json' -d'
{
  "query": { "match_all": {} },
  "sort": [{ "timestamp": { "order": "desc" } }],
  "size": 20
}'
```
- To filter by log type
```bash
curl "localhost:9200/game-backlog-logs/_search?pretty" \
  -H 'Content-Type: application/json' -d'
{
  "query": { "term": { "log_type": "ERROR" } }
}'
```

- To get slow requests 
```bash
curl "localhost:9200/game-backlog-logs/_search?pretty" \
  -H 'Content-Type: application/json' -d'
{
  "query": { "range": { "processing_time_ms": { "gte": 200 } } }
}'
```

## Background Tasks

### Celery Commands

Start Celery worker:
```bash
celery -A app.core.celery_app worker --loglevel=info
```

Run weekly stats manually:
```bash
celery -A app.core.celery_app call app.tasks.export_tasks.generate_weekly_stats
```

Check task status:
```bash
celery -A app.core.celery_app inspect active
```

