import typer

from app.db.session import AsyncSessionLocal
from app.services.user_service import UserService


async def create_superuser() -> None:
    """Interactively create a superuser"""

    async with AsyncSessionLocal() as session:
        email = typer.prompt("Admin Email", default="admin@notify.com")
        username = typer.prompt("Admin Username")
        password = typer.prompt("Admin Password", hide_input=True)
        confirm_password = typer.prompt("Confirm Password", hide_input=True)

        if password != confirm_password:
            typer.echo("Passwords do not match")
            raise typer.Exit()

        try:
            await UserService(session).create_superuser(username, email, password)
            typer.echo(f"    [+] Successfully created superuser: {email or username}")
        except Exception as e:
            typer.echo(f"Failed to create superuser: {e} ")

        await session.commit()
