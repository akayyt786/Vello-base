#!/usr/bin/env python
"""
Own Firebase CLI (Phase 1 MVP scaffold).
Future: Project init, rules compilation, emulator control, deployments.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ownfirebase.settings')
django.setup()

from typer import Typer
import typer

app = Typer(help="Own Firebase CLI")


@app.command()
def init(project_name: str, slug: str = None):
    """Initialize a new Own Firebase project."""
    typer.echo(f"Initializing project: {project_name}")
    if slug is None:
        slug = project_name.lower().replace(' ', '-')
    typer.echo(f"  Slug: {slug}")
    typer.echo("[+] Phase 2: Project creation implementation")


@app.command()
def rules(action: str = "get", path: str = None):
    """Get or update security rules."""
    if action == "get":
        typer.echo("[+] Phase 2: Fetch security rules from project")
    elif action == "update":
        typer.echo(f"[+] Phase 2: Update rules from {path}")
    elif action == "test":
        typer.echo("[+] Phase 2: Test rules against sample data")
    else:
        typer.echo(f"Unknown action: {action}")


@app.command()
def emulator(action: str = "start"):
    """Control local emulator."""
    if action == "start":
        typer.echo("[+] Phase 2: Start local emulator (docker-compose)")
    elif action == "stop":
        typer.echo("[+] Phase 2: Stop local emulator")
    elif action == "reset":
        typer.echo("[+] Phase 2: Reset local emulator data")
    else:
        typer.echo(f"Unknown action: {action}")


@app.command()
def deploy(target: str = "staging"):
    """Deploy to cloud."""
    typer.echo(f"[+] Phase 2: Deploy to {target} environment")
    typer.echo("   Steps:")
    typer.echo("   1. Build Docker image")
    typer.echo("   2. Push to registry")
    typer.echo("   3. Trigger deployment")


@app.command()
def shell():
    """Interactive Django shell."""
    from django.core.management import call_command
    call_command('shell')


if __name__ == '__main__':
    app()
