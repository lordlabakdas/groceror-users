# groceror-users

Microservice that consumes user lifecycle events from RabbitMQ, stores them as an immutable event log in MongoDB, and exposes Prometheus metrics for Grafana dashboarding.

Published by the [groceror](https://github.com/lordlabakdas/groceror) main service. Can run as a long-running container or as an AWS Lambda function.

---

## Events consumed

| Event | Trigger |
|---|---|
| `user_registered` | New user/store registration |
| `otp_verified` | OTP successfully verified |
| `profile_updated` | User or store profile created/updated |
| `password_changed` | Password successfully changed |

All events are stored in MongoDB (`users` database, `user_events` collection) and never modified after insert.

---

## Running alongside groceror

groceror runs as a bare Python process (`make run`) and expects RabbitMQ on `localhost:5672`. groceror-users runs in Docker Compose and connects to that same broker via `host.docker.internal`.

**1. Start RabbitMQ on your host** (if not already running):

```bash
# macOS
brew services start rabbitmq

# Linux
sudo systemctl start rabbitmq-server

# or via Docker (standalone)
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

**2. Start groceror:**

```bash
cd /path/to/groceror
make run   # starts on localhost:8000
```

**3. Start groceror-users:**

```bash
docker compose up --build
```

The compose stack defaults `RABBITMQ_HOST=host.docker.internal`, which routes from inside the container to RabbitMQ on your host — no extra config needed.

**Verify it's working:**

Trigger any user event on groceror (`POST /user/register`, `POST /user/verify-otp`, `POST /user/set-profile`, `PUT /user/change-password`), then check:

```bash
# event landed in MongoDB
mongosh mongodb://localhost:27018/users --eval "db.user_events.find().pretty()"

# metric incremented
curl -s localhost:8002/metrics | grep groceror_users_events_total
```

Open Grafana at http://localhost:3001 (admin / admin) — the **User Events** dashboard shows activity in real time.

**RabbitMQ management UI** (if using the `rabbitmq:3-management` image) is at http://localhost:15672 (guest / guest). `user_events_queue` and `user_events_queue.dlq` appear once groceror-users starts.

---

## Running with Docker Compose

The compose stack includes groceror-users, MongoDB, Prometheus, and Grafana.

**Prerequisite:** groceror must already be running with its RabbitMQ instance accessible from the host.

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| groceror-users API | http://localhost:8002 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / admin) |
| MongoDB | localhost:27018 |

The Grafana dashboard (`User Events`) is provisioned automatically on startup.

---

## Running locally (without Docker)

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for tests only

# start the service
python main.py
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `RABBITMQ_HOST` | `localhost` | RabbitMQ broker hostname |
| `RABBITMQ_PORT` | `5672` | RabbitMQ broker port |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASS` | `guest` | RabbitMQ password |
| `RABBITMQ_VHOST` | `/` | RabbitMQ virtual host |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `API_HOST` | `0.0.0.0` | FastAPI bind address |
| `API_PORT` | `8002` | FastAPI port |
| `METRICS_BACKEND` | `prometheus` | `prometheus` (container) or `pushgateway` (Lambda) |
| `PUSHGATEWAY_URL` | _(empty)_ | Pushgateway URL, required when `METRICS_BACKEND=pushgateway` |

For production, override at minimum:

```bash
RABBITMQ_HOST=<broker-host>
RABBITMQ_PASS=<strong-password>
MONGO_URI=mongodb://<user>:<password>@<host>:27017/users
```

### Using a `.env` file

The Docker Compose file reads from a `.env` file in the project root:

```dotenv
RABBITMQ_HOST=my-broker.internal
RABBITMQ_USER=groceror
RABBITMQ_PASS=changeme
```

---

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Returns `{"status": "ok"}` |
| `GET /metrics` | Prometheus metrics (text/plain) |

---

## Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `groceror_users_events_total` | Counter | `event_type` | Successfully stored events |
| `groceror_users_processing_errors_total` | Counter | `event_type`, `reason` | Validation, schema, or DB errors |
| `groceror_users_consumer_up` | Gauge | — | `1` when connected, `0` otherwise |

---

## AWS Lambda deployment

`lambda_handler.py` supports Amazon MQ and SQS triggers. The handler function is `lambda_handler.handler`.

Set these environment variables on the Lambda function:

```
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>/users
METRICS_BACKEND=pushgateway
PUSHGATEWAY_URL=https://<pushgateway-host>
RABBITMQ_HOST=<broker-host>   # informational; not used by Lambda directly
```

The Lambda entry point shares the same `handler.process_message` core as the container — no business logic is duplicated.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
