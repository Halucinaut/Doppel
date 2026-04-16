import typer

from doppel.cli.commands.run import run
from doppel.cli.commands.validate import validate

app = typer.Typer(help="Doppel synthetic user testing CLI")

app.command()(run)
app.command()(validate)


if __name__ == "__main__":
    app()
