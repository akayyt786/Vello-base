#!/usr/bin/env python3
"""
OwnFirebase CLI — orchestrate your self-hosted Firebase replacement.

Commands are thin wrappers around docker-compose and standard Django management
commands. All subprocess calls use subprocess.run() with explicit error handling.
"""

import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="own",
    help="OwnFirebase CLI — manage your self-hosted Firebase stack.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Resolve the project root as the directory that contains this cli.py file so
# the CLI works regardless of the caller's current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
COMPOSE_PROD_FILE = PROJECT_ROOT / "docker-compose.prod.yml"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"

# The Django application service name as defined in docker-compose.yml.
DJANGO_SERVICE = "django"

VERSION = "0.5.0"
PHASE = "Phase 5A"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compose(*args: str, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a docker-compose command rooted at PROJECT_ROOT."""
    cmd = ["docker-compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=check, **kwargs)


def _compose_exec(service: str, *args: str) -> subprocess.CompletedProcess:
    """Run a command inside a running compose service."""
    return _compose("exec", service, *args)


def _print_ok(msg: str) -> None:
    typer.echo(typer.style(f"  [OK] {msg}", fg=typer.colors.GREEN))


def _print_info(msg: str) -> None:
    typer.echo(typer.style(f"  --> {msg}", fg=typer.colors.CYAN))


def _print_warn(msg: str) -> None:
    typer.echo(typer.style(f"  [!] {msg}", fg=typer.colors.YELLOW), err=True)


def _print_err(msg: str) -> None:
    typer.echo(typer.style(f"  [ERROR] {msg}", fg=typer.colors.RED), err=True)


def _abort(msg: str) -> None:
    _print_err(msg)
    raise typer.Exit(code=1)


def _require_compose_file() -> None:
    if not COMPOSE_FILE.exists():
        _abort(f"docker-compose.yml not found at {COMPOSE_FILE}. Are you in the right directory?")


def _require_env_file() -> None:
    if not ENV_FILE.exists():
        _abort(".env not found. Run `own init` first.")


def _replace_env_value(content: str, key: str, value: str) -> str:
    """Replace or append a KEY=value line in .env file content."""
    pattern = rf"^{re.escape(key)}=.*$"
    replacement = f"{key}={value}"
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count == 0:
        # Key didn't exist — append it.
        new_content = new_content.rstrip("\n") + f"\n{replacement}\n"
    return new_content


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """Initialize a new OwnFirebase project."""
    typer.echo(typer.style("\nOwnFirebase — Project Initializer", bold=True))
    typer.echo("─" * 44)

    project_name: str = typer.prompt("  Project name", default="ownfirebase")
    admin_email: str = typer.prompt("  Admin email")
    admin_password: str = typer.prompt("  Admin password", hide_input=True, confirmation_prompt=True)

    # Derive a safe DB name from the project name.
    db_name = re.sub(r"[^a-z0-9_]", "_", project_name.lower())

    # ------------------------------------------------------------------
    # Create .env from .env.example
    # ------------------------------------------------------------------
    if ENV_FILE.exists():
        overwrite = typer.confirm("\n  .env already exists. Overwrite?", default=False)
        if not overwrite:
            _print_warn("Aborted — existing .env preserved.")
            raise typer.Exit(code=0)

    if not ENV_EXAMPLE_FILE.exists():
        _abort(f".env.example not found at {ENV_EXAMPLE_FILE}")

    shutil.copy(str(ENV_EXAMPLE_FILE), str(ENV_FILE))
    _print_ok(".env created from .env.example")

    # Populate generated/user-supplied values.
    content = ENV_FILE.read_text()
    secret_key = secrets.token_hex(50)
    jwt_key = secrets.token_hex(32)
    db_password = secrets.token_hex(16)

    content = _replace_env_value(content, "DJANGO_SECRET_KEY", secret_key)
    content = _replace_env_value(content, "JWT_SIGNING_KEY", jwt_key)
    content = _replace_env_value(content, "DATABASE_NAME", db_name)
    content = _replace_env_value(content, "DATABASE_PASSWORD", db_password)
    content = _replace_env_value(content, "DEBUG", "False")

    ENV_FILE.write_text(content)
    _print_ok(f"DJANGO_SECRET_KEY generated ({len(secret_key)} hex chars)")
    _print_ok(f"DATABASE_NAME set to '{db_name}'")
    _print_ok(f"DATABASE_PASSWORD auto-generated")

    typer.echo("\n" + typer.style("  Admin credentials (use these with `own createsuperuser`)", fg=typer.colors.YELLOW))
    typer.echo(f"    Email:    {admin_email}")
    typer.echo(f"    Password: {'*' * len(admin_password)}")

    typer.echo("\n" + typer.style("  Next steps:", bold=True))
    typer.echo("    1.  own up        — start all services")
    typer.echo("    2.  own migrate   — apply database migrations")
    typer.echo("    3.  own createsuperuser  — create your admin user")
    typer.echo("    4.  own status    — verify everything is healthy\n")


@app.command()
def up(
    build: bool = typer.Option(False, "--build", help="Rebuild images before starting."),
    logs: bool = typer.Option(False, "--logs", help="Tail logs after services start."),
) -> None:
    """Start all OwnFirebase services (docker-compose up -d)."""
    _require_compose_file()
    _require_env_file()

    typer.echo(typer.style("\nStarting OwnFirebase services...", bold=True))

    args = ["up", "-d"]
    if build:
        args.append("--build")

    try:
        _compose(*args)
    except subprocess.CalledProcessError as exc:
        _abort(f"docker-compose up failed (exit {exc.returncode}).")

    # Give services a moment to initialize then print URLs.
    _print_info("Waiting for services to initialize...")
    time.sleep(3)

    typer.echo(typer.style("\n  Service URLs:", bold=True))
    typer.echo("    Django API   →  http://localhost:8000")
    typer.echo("    API Docs     →  http://localhost:8000/api/docs/")
    typer.echo("    Django Admin →  http://localhost:8000/admin/")
    typer.echo("    MinIO        →  http://localhost:9001  (object storage console)")
    typer.echo("    PostgreSQL   →  localhost:5432")
    typer.echo("    Redis        →  localhost:6379\n")

    if logs:
        typer.echo(typer.style("  Tailing logs (Ctrl-C to stop)...\n", fg=typer.colors.CYAN))
        try:
            _compose("logs", "-f", check=False)
        except KeyboardInterrupt:
            pass


@app.command()
def down(
    volumes: bool = typer.Option(
        False, "--volumes", "-v", help="Remove named volumes (DESTROYS all data)."
    ),
) -> None:
    """Stop all OwnFirebase services."""
    _require_compose_file()

    if volumes:
        confirmed = typer.confirm(
            typer.style(
                "  WARNING: --volumes will permanently delete all PostgreSQL, Redis and MinIO data. Continue?",
                fg=typer.colors.RED,
            ),
            default=False,
        )
        if not confirmed:
            _print_warn("Aborted.")
            raise typer.Exit(code=0)

    typer.echo(typer.style("\nStopping OwnFirebase services...", bold=True))
    args = ["down"]
    if volumes:
        args.append("-v")

    try:
        _compose(*args)
    except subprocess.CalledProcessError as exc:
        _abort(f"docker-compose down failed (exit {exc.returncode}).")

    _print_ok("All services stopped.")
    if volumes:
        _print_warn("Volumes removed — data has been deleted.")
    typer.echo()


@app.command()
def status() -> None:
    """Check the status of all OwnFirebase services."""
    _require_compose_file()

    typer.echo(typer.style("\nOwnFirebase Service Status", bold=True))
    typer.echo("─" * 44)

    try:
        _compose("ps", check=False)
    except subprocess.CalledProcessError:
        _print_warn("docker-compose ps failed — are services running?")

    # Health-check the Django API.
    typer.echo(typer.style("\n  API Health Check:", bold=True))
    try:
        import urllib.request
        import json

        url = "http://localhost:8000/api/health/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode()
            try:
                data = json.loads(body)
                _print_ok(f"GET {url}  →  {data}")
            except json.JSONDecodeError:
                _print_ok(f"GET {url}  →  {body[:200]}")
    except Exception as exc:
        _print_warn(f"Could not reach {url}: {exc}")
        _print_info("Run `own up` if services are not started.")

    typer.echo()


@app.command()
def logs(
    service: Optional[str] = typer.Option(
        None, "--service", "-s", help="Service name (default: all services)."
    ),
) -> None:
    """Tail logs from one or all services."""
    _require_compose_file()

    typer.echo(
        typer.style(
            f"\nTailing logs for: {service or 'all services'}  (Ctrl-C to stop)\n",
            bold=True,
        )
    )

    args = ["logs", "-f"]
    if service:
        args.append(service)

    try:
        _compose(*args, check=False)
    except KeyboardInterrupt:
        typer.echo("\n")
    except subprocess.CalledProcessError as exc:
        _abort(f"docker-compose logs failed (exit {exc.returncode}).")


@app.command()
def migrate() -> None:
    """Apply Django database migrations inside the running container."""
    _require_compose_file()

    typer.echo(typer.style("\nRunning Django migrations...", bold=True))
    try:
        _compose_exec(DJANGO_SERVICE, "python", "manage.py", "migrate")
    except subprocess.CalledProcessError as exc:
        _abort(f"migrate failed (exit {exc.returncode}). Is the '{DJANGO_SERVICE}' container running?")

    _print_ok("Migrations complete.\n")


@app.command()
def createsuperuser() -> None:
    """Create a Django admin superuser interactively."""
    _require_compose_file()

    typer.echo(typer.style("\nCreating Django superuser...\n", bold=True))
    try:
        _compose_exec(DJANGO_SERVICE, "python", "manage.py", "createsuperuser")
    except subprocess.CalledProcessError as exc:
        _abort(f"createsuperuser failed (exit {exc.returncode}). Is the '{DJANGO_SERVICE}' container running?")


@app.command()
def shell() -> None:
    """Open an interactive Django shell inside the running container."""
    _require_compose_file()

    typer.echo(typer.style("\nOpening Django shell...\n", bold=True))
    try:
        _compose_exec(DJANGO_SERVICE, "python", "manage.py", "shell")
    except subprocess.CalledProcessError as exc:
        _abort(f"shell failed (exit {exc.returncode}). Is the '{DJANGO_SERVICE}' container running?")


@app.command()
def deploy() -> None:
    """Deploy OwnFirebase using the production compose overrides."""
    _require_compose_file()
    _require_env_file()

    # Pre-flight checks.
    typer.echo(typer.style("\nPre-flight checks...", bold=True))

    if not COMPOSE_PROD_FILE.exists():
        _abort(f"docker-compose.prod.yml not found at {COMPOSE_PROD_FILE}")

    content = ENV_FILE.read_text()
    if "DJANGO_SECRET_KEY=dev-secret-key" in content or "DJANGO_SECRET_KEY=" not in content:
        _abort(
            "DJANGO_SECRET_KEY in .env looks like the default or is missing. "
            "Generate a real key with: python -c \"import secrets; print(secrets.token_hex(50))\""
        )

    _print_ok(".env found with non-default SECRET_KEY")
    _print_ok(f"docker-compose.prod.yml found at {COMPOSE_PROD_FILE}")

    typer.echo(typer.style("\nDeploying with production overrides...", bold=True))
    cmd = [
        "docker-compose",
        "-f", str(COMPOSE_FILE),
        "-f", str(COMPOSE_PROD_FILE),
        "up", "-d", "--build",
    ]
    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    except subprocess.CalledProcessError as exc:
        _abort(f"Deployment failed (exit {exc.returncode}).")

    _print_ok("Deployment complete!")
    typer.echo(typer.style("\n  Deployed! Run `own status` to verify all services are healthy.\n", bold=True))


@app.command()
def version() -> None:
    """Print OwnFirebase CLI version information."""
    typer.echo(typer.style(f"\nOwnFirebase v{VERSION} ({PHASE})\n", bold=True))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
