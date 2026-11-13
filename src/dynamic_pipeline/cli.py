"""Command-line entry point for the initial pipeline scaffold."""

import click


@click.command(
    help=(
        "Tender pipeline scaffold. "
        "PDF extraction and OKF generation are not implemented yet."
    )
)
def main():
    click.echo(
        "Pipeline foundation is available. "
        "Extraction and OKF generation are not implemented yet."
    )


if __name__ == "__main__":
    main()
