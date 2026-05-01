# Notify

Async SaaS notification platform — lifecycle email & SMS hooks with subscription management.

Built with **FastAPI**, **Celery**, **SQLAlchemy async**, **PostgreSQL**, **Redis**, **Twilio**, and **Stripe**.

---


## Scripts 
Creating a superuser with admin privilege
> python manage.py createsuperuser
> 
Seeding database with plans
> python manage.py seed
> 
> 
---
## Docker
Building a docker image
> docker image build -t tag_name .

Starting up a docker container
>docker container run --name container_name -d -p 8000:8000 tag_name

Docker compose 

Up:
>   docker compose up

Down: 
>   docker compose down

---

Linting
> uv run ruff check [directory_path | file_path]

Formatting 
> uv run ruff format [directory_path | file_path]