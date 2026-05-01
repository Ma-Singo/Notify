import typer
import asyncio

from scripts.seed_db import seed_db
from scripts.create_superuser import create_superuser



app = typer.Typer()


@app.command()
def createsuperuser():
    asyncio.run(create_superuser())


@app.command()
def seed():
    asyncio.run(seed_db())
    typer.echo("Database seeded successfully.")



if __name__ == "__main__":
    app()
