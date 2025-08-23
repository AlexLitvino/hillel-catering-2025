# hillel-catering-2025

# Project Setup

## Local  setup
Ensure that you have `pipenv` installed on your system.  
```shell
pipx install pipenv
```
Install project dependencies
```shell
pipenv shell  &&  pipenv sync
```
Apply migrations to DB
```shell
python manage.py migrate
```
Create superuser
```shell
python manage.py createsuperuser
```
Load test data into database
```shell
python manage.py loaddata fixtures/dump.json
```

## Docker setup

Create `.env` file with the following variables specified:
```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=catering

DJANGO_SECRET_KEY = "<DJANGO_SECRET_KEY>"
DJANGO_DEBUG=1
```
Export environment variables
```shell
source .env
```
Build application image
```shell
docker compose build
```
Start application-related  containers
```shell
docker compose up
```
Apply migrations to DB
```shell
docker compose exec api python manage.py migrate
```
Create superuser
```shell
docker compose exec api python manage.py createsuperuser
```
Load test data into your database
```shell
docker compose exec api python manage.py loaddata /app/fixtures/dump.json
```
To stop application with containers removal run
```shell
docker compose down
```
