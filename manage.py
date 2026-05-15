import typer
import asyncio

from scripts.seed_db import seed_db
from scripts.create_superuser import create_superuser
from scripts.sync_stripe_plans import sync_stripe_plans


app = typer.Typer()


@app.command()
def createsuperuser():
    asyncio.run(create_superuser())


@app.command()
def seed():
    """Seed the database with initial data"""
    try:
        asyncio.run(seed_db())
        typer.echo("Database seeded successfully.")
    except Exception as e:
        typer.echo(f"Seeding failed: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def sync_stripe():
    asyncio.run(sync_stripe_plans())


if __name__ == "__main__":
    app()
