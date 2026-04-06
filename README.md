# backloggd replica

This is replica for popular game completion tracker tool **backloggd**

# API Endpoints Reference

## Auth
| Method | Endpoint | Access |
|--------|----------|--------|
| POST | `/api/auth/register` | public |
| POST | `/api/auth/login` | public |
| POST | `/api/auth/logout` | authenticated |
| GET | `/api/auth/me` | authenticated |

## Games
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/games` | public |
| GET | `/api/games/{id}` | public |
| POST | `/api/games` | admin only |
| PUT | `/api/games/{id}` | admin only |
| DELETE | `/api/games/{id}` | admin only |

## Platforms
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/platforms` | public |
| GET | `/api/platforms/{id}` | public |
| POST | `/api/platforms` | admin only |
| DELETE | `/api/platforms/{id}` | admin only |

## Backlog
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/backlog` | owner only |
| GET | `/api/backlog/{id}` | owner only |
| POST | `/api/backlog` | authenticated |
| PUT | `/api/backlog/{id}` | owner only |
| DELETE | `/api/backlog/{id}` | owner only |

## Reviews
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/reviews` | public |
| GET | `/api/reviews/{id}` | public |
| POST | `/api/reviews` | authenticated |
| PUT | `/api/reviews/{id}` | owner / moderator / admin |
| DELETE | `/api/reviews/{id}` | owner / moderator / admin |

## Tags
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/tags` | public |
| POST | `/api/tags` | authenticated |
| DELETE | `/api/tags/{id}` | owner / moderator / admin |
| POST | `/api/backlog/{id}/tags/{tag_id}` | owner only |
| DELETE | `/api/backlog/{id}/tags/{tag_id}` | owner only |

## Screenshots
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/backlog/{entry_id}/screenshots` | owner only |
| POST | `/api/backlog/{entry_id}/screenshots` | owner only |
| DELETE | `/api/backlog/{entry_id}/screenshots/{screenshot_id}` | owner only |

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

Check task status:
```bash
celery -A app.core.celery_app inspect active
```

