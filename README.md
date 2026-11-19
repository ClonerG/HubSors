# HubSors — Async IoT Sensor Hub & QA Automation Suite

![CI Status](https://github.com/ClonerG/HubSors/actions/workflows/test.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi&logoColor=white)
![Pytest](https://img.shields.io/badge/Tested%20with-Pytest%20%2B%20Allure-orange)

Asynchronous IoT sensor hub built with **FastAPI** and **PostgreSQL**, featuring background device polling, API key authentication, and a multi-layered automated test suite (**Unit**, **Integration**, and **Security** tests).

## Key Features

* **Background Polling (`asyncio`):** Periodically pings connected sensors, monitors critical battery levels (less than 20%), fetches firmware versions via `aiohttp`, and logs telemetry into PostgreSQL.
* **API Security:** Protects the `GET /api/logs` endpoint with `X-API-Key` header validation (`401` when missing, `403` when invalid).
* **Automated QA Suite (`pytest` + `Allure`):**
  * **Unit tests:** Battery level parameterization, duplicate device handling, offline exceptions, and `pytest-mock` simulation of external API timeouts/500 errors.
  * **Integration tests:** End-to-end database writes and reads via `httpx.AsyncClient` against a real PostgreSQL instance (verifying `LIMIT 10` and `DESC` timestamp sorting).
  * **Security tests:** Unauthorized and invalid API key access checks.

## Tech Stack

* **Backend & DB:** Python 3.13, FastAPI, SQLAlchemy (Async + `NullPool`), PostgreSQL (`asyncpg`), `aiohttp`
* **Testing & CI/CD:** Pytest, `pytest-asyncio`, `pytest-mock`, `httpx`, Allure Report, Docker Compose, GitHub Actions

## Quick Start (Docker Compose)

1. Clone the repository and start the containers:
```bash
git clone https://github.com/ClonerG/HubSors.git
cd HubSors
docker compose up -d --build
```
2. Test the API:
* **Swagger UI:** open `http://localhost:8000/docs`, click **Authorize**, and enter your `X-API-Key`.
* **Terminal request:**
```bash
curl -H "X-API-Key: asdjtjassad-dsa" http://localhost:8000/api/logs
```
## Running Tests & Allure Report
Run all tests inside the Docker container and save results for Allure:
```bash
docker compose exec app pytest --alluredir=allure-results
```
Open the visual Allure report in your browser:
```bash
allure serve allure-results
```