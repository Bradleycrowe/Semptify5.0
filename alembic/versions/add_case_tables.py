"""Add Case, CaseDocument, and CaseEvent tables

Revision ID: add_case_tables
Revises: 4662caf39763
Create Date: 2025-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_case_tables'
down_revision: Union[str, None] = '4662caf39763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Case management tables."""
    
    # Create cases table
    op.create_table(
        'cases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('case_number', sa.String(100), nullable=False),
        sa.Column('court', sa.String(255), nullable=True),
        sa.Column('case_type', sa.String(50), nullable=True),
        sa.Column('plaintiffs', sa.Text, nullable=True),  # JSON array
        sa.Column('defendants', sa.Text, nullable=True),  # JSON array
        sa.Column('property_address', sa.String(255), nullable=True),
        sa.Column('property_unit', sa.String(50), nullable=True),
        sa.Column('property_city', sa.String(100), nullable=True),
        sa.Column('property_state', sa.String(2), nullable=True),
        sa.Column('property_zip', sa.String(20), nullable=True),
        sa.Column('date_filed', sa.DateTime, nullable=True),
        sa.Column('date_served', sa.DateTime, nullable=True),
        sa.Column('answer_deadline', sa.DateTime, nullable=True),
        sa.Column('hearing_date', sa.DateTime, nullable=True),
        sa.Column('amount_claimed', sa.Float, nullable=True),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on case_number
    op.create_index('ix_cases_case_number', 'cases', ['case_number'])
    op.create_index('ix_cases_user_id', 'cases', ['user_id'])
    
    # Create case_documents table
    op.create_table(
        'case_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('document_type', sa.String(50), nullable=True),  # complaint, lease, notice, etc.
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('extracted_text', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create index on case_id
    op.create_index('ix_case_documents_case_id', 'case_documents', ['case_id'])
    
    # Create case_events table
    op.create_table(
        'case_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=True),  # filing, hearing, deadline, etc.
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('event_date', sa.DateTime, nullable=True),
        sa.Column('document_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create index on case_id
    op.create_index('ix_case_events_case_id', 'case_events', ['case_id'])
    op.create_index('ix_case_events_event_date', 'case_events', ['event_date'])


def downgrade() -> None:
    """Drop Case management tables."""
    op.drop_table('case_events')
    op.drop_table('case_documents')
    op.drop_table('cases')
