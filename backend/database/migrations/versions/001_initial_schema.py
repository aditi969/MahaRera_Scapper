"""Initial schema for RERA Insight

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-14 19:43:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

def upgrade() -> None:
    # 1. Projects
    op.create_table(
        'projects',
        sa.Column('rera_id', sa.String(length=32), primary_key=True),
        sa.Column('registration_number', sa.String(length=64), nullable=True),
        sa.Column('date_of_registration', sa.Date(), nullable=True),
        sa.Column('project_name', sa.String(length=255), nullable=True),
        sa.Column('project_location', sa.Text(), nullable=True),
        sa.Column('project_type', sa.String(length=64), nullable=True),
        sa.Column('project_status', sa.String(length=64), nullable=True),
        sa.Column('district', sa.String(length=64), nullable=True),
        sa.Column('taluka', sa.String(length=64), nullable=True),
        sa.Column('village', sa.String(length=128), nullable=True),
        sa.Column('state_ut', sa.String(length=64), nullable=True),
        sa.Column('locality', sa.String(length=255), nullable=True),
        sa.Column('pin_code', sa.String(length=16), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('survey_no', sa.String(length=255), nullable=True),
        sa.Column('total_land_area', sa.String(length=64), nullable=True),
        sa.Column('permissible_builtup_area', sa.String(length=64), nullable=True),
        sa.Column('sanctioned_builtup_area', sa.String(length=64), nullable=True),
        sa.Column('project_completion_date_original', sa.Date(), nullable=True),
        sa.Column('project_completion_date_revised', sa.Date(), nullable=True),
        sa.Column('boundaries_east', sa.Text(), nullable=True),
        sa.Column('boundaries_west', sa.Text(), nullable=True),
        sa.Column('boundaries_south', sa.Text(), nullable=True),
        sa.Column('boundaries_north', sa.Text(), nullable=True),
        sa.Column('promoter_details', sa.Text(), nullable=True),
        sa.Column('has_investors', sa.String(length=16), nullable=True),
        sa.Column('past_experience_info', sa.Text(), nullable=True),
        sa.Column('litigations', sa.Text(), nullable=True),
        sa.Column('bank_name', sa.String(length=128), nullable=True),
        sa.Column('ifsc_code', sa.String(length=32), nullable=True),
        sa.Column('bank_address', sa.Text(), nullable=True),
        sa.Column('bhk_details', JSON_TYPE, nullable=True),
        sa.Column('building_details', JSON_TYPE, nullable=True),
        sa.Column('summary_of_apartments', JSON_TYPE, nullable=True),
        sa.Column('all_parking_details', JSON_TYPE, nullable=True),
        sa.Column('organization', sa.String(length=128), nullable=True),
        sa.Column('last_modified', sa.String(length=64), nullable=True),
        sa.Column('commencing_from', sa.Date(), nullable=True),
        sa.Column('leftmost_date', sa.Date(), nullable=True),
        sa.Column('ending_with', sa.Date(), nullable=True),
        sa.Column('cert_date_source', sa.String(length=64), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('scrape_job_id', sa.String(length=64), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('validation_status', sa.String(length=32), server_default='VALID', nullable=True),
        sa.Column('validation_errors', JSON_TYPE, nullable=True),
        sa.Column('extraction_errors', JSON_TYPE, nullable=True),
        sa.Column('cert_extraction_status', sa.String(length=32), server_default='PENDING', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_projects_district', 'projects', ['district'])
    op.create_index('idx_projects_status', 'projects', ['project_status'])
    op.create_index('idx_projects_type', 'projects', ['project_type'])

    # 2. Scrape Jobs
    op.create_table(
        'scrape_jobs',
        sa.Column('job_id', sa.String(length=64), primary_key=True),
        sa.Column('district_name', sa.String(length=64), nullable=False),
        sa.Column('district_code', sa.String(length=16), nullable=False),
        sa.Column('start_page', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('end_page', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('headless', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('max_workers', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('projects_found', sa.Integer(), server_default='0'),
        sa.Column('projects_extracted', sa.Integer(), server_default='0'),
        sa.Column('projects_failed', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 3. Scrape Logs
    op.create_table(
        'scrape_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.String(length=64), sa.ForeignKey('scrape_jobs.job_id', ondelete='CASCADE')),
        sa.Column('level', sa.String(length=16), nullable=False, server_default='INFO'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('extra', JSON_TYPE, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 4. Data Quality Checks
    op.create_table(
        'data_quality_checks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('check_name', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('total_evaluated', sa.Integer(), server_default='0'),
        sa.Column('failures_count', sa.Integer(), server_default='0'),
        sa.Column('pass_rate', sa.Float(), server_default='100.0'),
        sa.Column('details', JSON_TYPE, nullable=True),
        sa.Column('run_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('data_quality_checks')
    op.drop_table('scrape_logs')
    op.drop_table('scrape_jobs')
    op.drop_table('projects')

