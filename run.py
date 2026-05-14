import logging
import click
from app.config import APP_HOST, APP_PORT, BUCKETS, REPORT_PERIODS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@click.group()
def cli():
    """Auto-Researcher MVP — Ingest, classify, and report on AI research papers."""


@cli.command()
@click.option("--query", default=None, help="arXiv search query (default: category-based)")
@click.option("--max-results", default=None, type=int, help="Max papers per bucket")
@click.option("--bucket", default=None, type=click.Choice(BUCKETS), help="Only ingest this bucket")
def ingest(query, max_results, bucket):
    """Fetch papers from arXiv, extract text, and store in database."""
    from app.ingestion.pipeline import run_ingestion
    added, _ = run_ingestion(query=query, max_results=max_results, bucket=bucket)
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
@click.option("--period", type=click.Choice(REPORT_PERIODS), required=True)
def report(period):
    """Generate a research report for a time period."""
    from app.reports.generator import generate_report
    result = generate_report(period)
    click.echo(f"Report generated: {result}")


@cli.command(name="pipeline")
@click.option("--max-results", default=None, type=int, help="Max papers per bucket")
@click.option("--period", default="7d", type=click.Choice(REPORT_PERIODS), help="Report period")
@click.option("--query", default=None, help="arXiv search query (default: category-based)")
@click.option("--bucket", default=None, type=click.Choice(BUCKETS), help="Only ingest this bucket")
def run_pipeline(max_results, period, query, bucket):
    """Run the full pipeline: ingest → dedup → embed → classify → report."""
    from app.ingestion.pipeline import run_ingestion
    from app.classification.dedup import deduplicate
    from app.classification.embedder import embed_all_papers
    from app.classification.classifier import classify_all_papers
    from app.reports.generator import generate_report
    from app.metrics import track_pipeline

    with track_pipeline("full_pipeline") as ctx:
        click.echo("=== Step 1: Ingest ===")
        added, new_ids = run_ingestion(max_results=max_results, query=query, bucket=bucket)
        click.echo(f"  Ingested: {added} new papers")

        click.echo("=== Step 2: Dedup ===")
        removed = deduplicate(new_paper_ids=new_ids if new_ids else None)
        click.echo(f"  Removed: {removed} duplicates")

        click.echo("=== Step 3: Embed ===")
        embedded = embed_all_papers()
        click.echo(f"  Embedded: {embedded} papers")

        click.echo("=== Step 4: Classify ===")
        classified = classify_all_papers(paper_ids=new_ids if new_ids else None)
        click.echo(f"  Classified: {classified} papers")

        click.echo("=== Step 5: Report ===")
        result = generate_report(period)
        click.echo(f"  Report: {result}")

        ctx["paper_count"] = added
        ctx["stages_json"] = {
            "ingested": added,
            "deduplicated": removed,
            "embedded": embedded,
            "classified": classified,
            "report": result,
        }

    click.echo("Pipeline complete!")


@cli.command()
def resync():
    """Re-sync embeddings from SQLite to Pinecone (recover from dual-write drift)."""
    from app.classification.pinecone_store import resync_embeddings
    count = resync_embeddings()
    click.echo(f"Re-synced {count} papers from SQLite to Pinecone")


@cli.command()
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def serve(host, port):
    """Start the local dashboard with auto-ingest scheduler (1 paper/min)."""
    import uvicorn
    from app.main import create_app, _start_scheduler
    app = create_app()
    _start_scheduler()
    uvicorn.run(app, host=host or APP_HOST, port=port or APP_PORT)


if __name__ == "__main__":
    cli()