import logging
import click
from app.config import APP_HOST, APP_PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@click.group()
def cli():
    """Auto-Researcher MVP — Ingest, classify, and report on AI research papers."""


@cli.command()
@click.option("--query", default=None, help="arXiv search query (default: category-based)")
@click.option("--max-results", default=None, type=int, help="Max papers per bucket")
def ingest(query, max_results):
    """Fetch papers from arXiv, extract text, and store in database."""
    from app.ingestion.pipeline import run_ingestion
    added = run_ingestion(query=query, max_results=max_results)
    click.echo(f"Ingestion complete: {added} new papers stored")


@cli.command()
def dedup():
    """Remove duplicate papers using fuzzy title matching."""
    from app.classification.dedup import deduplicate
    removed = deduplicate()
    click.echo(f"Removed {removed} duplicates")


@cli.command()
def classify():
    """Embed and classify papers into research buckets."""
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    embedded = embed_all_papers()
    click.echo(f"Embedded {embedded} papers")
    classified = classify_all_papers()
    click.echo(f"Classified {classified} papers")


@cli.command()
@click.option("--period", type=click.Choice(["7d", "6m", "1y"]), required=True)
def report(period):
    """Generate a research report for a time period."""
    from app.reports.generator import generate_report
    result = generate_report(period)
    click.echo(f"Report generated: {result}")


@cli.command()
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def serve(host, port):
    """Start the local dashboard."""
    import uvicorn
    from app.main import create_app
    uvicorn.run(create_app(), host=host or APP_HOST, port=port or APP_PORT)


if __name__ == "__main__":
    cli()