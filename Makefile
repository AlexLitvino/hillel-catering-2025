install:
	pipenv lock && pipenv sync

installdev:
	pipenv lock && pipenv sync --dev

build:
	docker build -t catering-api .

docker:
	docker run --rm -p 8000:8000 catering-api

clean:
	docker image prune

worker_default:
	celery -A config worker -l INFO -Q default

worker_high:
	celery -A config worker -l INFO -Q high_priority
