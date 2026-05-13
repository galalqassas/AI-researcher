"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-05-13 05:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table('papers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('arxiv_id', sa.String(), unique=True, nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('authors', sa.String(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('published_date', sa.Date(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(), nullable=True),
        sa.Column('buckets', sa.String(), nullable=True),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
    )
    op.create_table('reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('period', sa.String(10), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('paper_count', sa.Integer(), nullable=True),
    )
    op.create_table('pipeline_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('stages_json', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('paper_count', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('pipeline_runs')
    op.drop_table('reports')
    op.drop_table('papers')