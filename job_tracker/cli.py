import click
from . import auth as localauth, config, scraper, sheets


# ---------------------------------------------------------------------------
# Custom group: dispatches to 'add' when the first arg isn't a subcommand
# ---------------------------------------------------------------------------


class _DefaultAddGroup(click.Group):
    """Allows `job <url>` as shorthand for `job add <url>`."""

    def parse_args(self, ctx, args):
        if args and not args[0].startswith("-") and args[0] not in self.commands:
            args = ["add"] + args
        return super().parse_args(ctx, args)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group(
    cls=_DefaultAddGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def main(ctx):
    """
    Log a job application to Google Sheets.

    \b
    Usage:
      job <url>
      job <url> --company Stripe --title "Software Engineer"
      job <url> --notes "Referral from Jane"

    \b
    First-time setup:
      job setup
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# job add (also invoked as `job <url>`)
# ---------------------------------------------------------------------------


@main.command()
@click.argument("url")
@click.option(
    "--company", "-c", default="", help="Company name (auto-detected if omitted)"
)
@click.option("--title", "-t", default="", help="Job title (auto-detected if omitted)")
@click.option("--notes", "-n", default="", help="Optional notes")
def add(url, company, title, notes):
    """Log a job application from a URL."""
    _add(url=url, company=company, title=title, notes=notes)


# ---------------------------------------------------------------------------
# Add logic
# ---------------------------------------------------------------------------


def _add(url: str, company: str, title: str, notes: str) -> None:
    try:
        cfg = config.load()
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e))

    columns = [
        c.strip().lower()
        for c in cfg.get("columns", "date,company,title,url,status,notes").split(",")
    ]
    needs_company = "company" in columns
    needs_title = "title" in columns

    # Auto-detect missing fields
    if (needs_company and not company) or (needs_title and not title):
        click.echo("🔍 Detecting job details from URL...")
        detected = scraper.fetch(url)
        if needs_company and not company:
            company = detected.company
        if needs_title and not title:
            title = detected.title

    # Prompt for anything still missing
    if needs_company and not company:
        company = click.prompt("Company name")
    if needs_title and not title:
        title = click.prompt("Job title")

    click.echo(f"📋 Adding: {company} — {title}")

    try:
        tab_name, row_number = sheets.append_job(
            spreadsheet_id=cfg["spreadsheet_id"],
            company=company,
            title=title,
            url=url,
            notes=notes,
            sheet_name=cfg.get("sheet_name", ""),
            columns=cfg.get("columns", "date,company,title,url,status,notes"),
            date_format=cfg.get("date_format", "%Y-%m-%d"),
        )
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        raise click.ClickException(str(e))

    click.echo(f'✅ Added to sheet "{tab_name}" at row {row_number}')


# ---------------------------------------------------------------------------
# job auth
# ---------------------------------------------------------------------------


@main.command()
def auth():
    """Authenticate with Google"""
    localauth.get_credentials()


def run_setup():
    from .config import CONFIG_FILE

    try:
        localauth.get_credentials()
        if not CONFIG_FILE.exists():
            config.init_wizard()

        click.echo("Setup complete!")

    except click.exceptions.Abort:
        click.echo("Setup cancelled")


@main.command()
def setup():
    run_setup()


# ---------------------------------------------------------------------------
# job config
# ---------------------------------------------------------------------------


@main.group(name="config")
def config_cmd():
    """Manage job-tracker configuration."""
    pass


@config_cmd.command("init")
def config_init():
    """Interactive setup wizard."""
    config.init_wizard()


@config_cmd.command("show")
def config_show():
    """Print current configuration."""
    config.show()


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value.

    \b
    Keys:
      spreadsheet_id    The Google Sheets ID from your sheet URL
      sheet_name        Which tab to write to (blank = last tab)
      credentials_file  Path to your Google OAuth credentials JSON
    """
    try:
        config.set_value(key, value)
    except ValueError as e:
        raise click.ClickException(str(e))
