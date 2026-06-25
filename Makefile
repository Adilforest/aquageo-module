.PHONY: up down build migrate makemigrations test logs ps shell createsuperuser

# Build images and start the full stack (db, redis, web, worker, beat).
up:
	docker compose up --build -d

# Stop and remove containers (keeps the pgdata volume).
down:
	docker compose down

build:
	docker compose build

# Apply migrations inside the web container.
migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

# Run the test suite inside the web container.
test:
	docker compose exec web pytest

logs:
	docker compose logs -f

ps:
	docker compose ps

shell:
	docker compose exec web python manage.py shell

createsuperuser:
	docker compose exec web python manage.py createsuperuser
