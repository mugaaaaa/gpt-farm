"""TUI mode (optional — requires textual)."""

import click

from .config import Config


def run_tui(cfg: Config) -> None:
    """Launch interactive TUI."""
    click.echo("TUI: pip install textual to enable")
    click.echo("For now, use CLI commands:")
    click.echo("  gpt-farm farm -n 5")
    click.echo("  gpt-farm push")
    click.echo("  gpt-farm status")
