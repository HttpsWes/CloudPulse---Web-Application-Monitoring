# CloudPulse AI — Day 1

A small local Flask application that provides a homepage, health and status APIs,
JSON request logs, and an opt-in, local-only demo error. AWS integration is planned
for later phases.

## Setup (macOS Terminal)

```bash
cd cloudpulse-ai
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000/>. In another terminal, try:

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/status
```

`--debug` is for local development only. Stop the server with Ctrl+C.

## Opt-in error demo

Stop the server, then start it with `ENABLE_DEMO_ERRORS=1 python -m flask --app app run --debug`.
From another terminal, request `curl -i http://127.0.0.1:5000/api/demo/error`.
The response is HTTP 500, and the terminal contains a JSON exception log and
a JSON request log. With the flag unset, this route returns 404. This route also
requires a direct request from localhost. Keep the flag unset on AWS.

## Checks

```bash
python -m unittest discover -s tests -v
```

Logs go to standard error. Every completed request has `status_code` and
`duration_ms`, making them useful later for CloudWatch Logs. The `/api/health`
route checks that the Flask process can respond; it does not verify AWS or any
other dependency.
