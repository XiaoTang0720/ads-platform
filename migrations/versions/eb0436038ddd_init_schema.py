"""init schema

Revision ID: eb0436038ddd
Revises: 
Create Date: 2026-11-22 11:04:32.591533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb0436038ddd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('advertiser',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_advertiser'))
    )
    op.create_table('campaign',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('advertiser_id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('targeting_type', sa.Enum('AUTO', 'MANUAL', name='targeting_type', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('daily_budget', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('status', sa.Enum('ENABLED', 'PAUSED', 'ARCHIVED', name='status', native_enum=False, create_constraint=True, length=16), server_default='ENABLED', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('daily_budget >= 0', name=op.f('ck_campaign_daily_budget_non_negative')),
    sa.ForeignKeyConstraint(['advertiser_id'], ['advertiser.id'], name=op.f('fk_campaign_advertiser_id_advertiser'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_campaign'))
    )
    op.create_index(op.f('ix_campaign_advertiser_id'), 'campaign', ['advertiser_id'], unique=False)
    op.create_table('ad_group',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('campaign_id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('default_bid', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('status', sa.Enum('ENABLED', 'PAUSED', 'ARCHIVED', name='status', native_enum=False, create_constraint=True, length=16), server_default='ENABLED', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('default_bid >= 0', name=op.f('ck_ad_group_default_bid_non_negative')),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaign.id'], name=op.f('fk_ad_group_campaign_id_campaign'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ad_group'))
    )
    op.create_index(op.f('ix_ad_group_campaign_id'), 'ad_group', ['campaign_id'], unique=False)
    op.create_table('ad',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('ad_group_id', sa.BigInteger(), nullable=False),
    sa.Column('asin', sa.String(length=10), nullable=False),
    sa.Column('status', sa.Enum('ENABLED', 'PAUSED', 'ARCHIVED', name='status', native_enum=False, create_constraint=True, length=16), server_default='ENABLED', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ad_group_id'], ['ad_group.id'], name=op.f('fk_ad_ad_group_id_ad_group'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ad')),
    sa.UniqueConstraint('ad_group_id', 'asin', name=op.f('uq_ad_ad_group_id_asin'))
    )
    op.create_table('keyword',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('ad_group_id', sa.BigInteger(), nullable=False),
    sa.Column('text', sa.String(length=200), nullable=False),
    sa.Column('match_type', sa.Enum('BROAD', 'PHRASE', 'EXACT', name='match_type', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('is_negative', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('bid', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('bid >= 0', name=op.f('ck_keyword_bid_non_negative')),
    sa.ForeignKeyConstraint(['ad_group_id'], ['ad_group.id'], name=op.f('fk_keyword_ad_group_id_ad_group'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_keyword')),
    sa.UniqueConstraint('ad_group_id', 'text', 'match_type', name=op.f('uq_keyword_ad_group_id_text_match_type'))
    )
    op.create_table('daily_metrics',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('ad_id', sa.BigInteger(), nullable=False),
    sa.Column('keyword_id', sa.BigInteger(), nullable=True),
    sa.Column('metric_date', sa.Date(), nullable=False),
    sa.Column('impressions', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('clicks', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('spend', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('orders', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('sales', sa.Numeric(precision=12, scale=2), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint('clicks <= impressions', name=op.f('ck_daily_metrics_clicks_lte_impressions')),
    sa.CheckConstraint('impressions >= 0 AND clicks >= 0 AND orders >= 0 AND spend >= 0 AND sales >= 0', name=op.f('ck_daily_metrics_non_negative')),
    sa.ForeignKeyConstraint(['ad_id'], ['ad.id'], name=op.f('fk_daily_metrics_ad_id_ad'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['keyword_id'], ['keyword.id'], name=op.f('fk_daily_metrics_keyword_id_keyword'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_metrics')),
    sa.UniqueConstraint('ad_id', 'keyword_id', 'metric_date', name=op.f('uq_daily_metrics_ad_id_keyword_id_metric_date'), postgresql_nulls_not_distinct=True)
    )
    op.create_index(op.f('ix_daily_metrics_keyword_id'), 'daily_metrics', ['keyword_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_daily_metrics_keyword_id'), table_name='daily_metrics')
    op.drop_table('daily_metrics')
    op.drop_table('keyword')
    op.drop_table('ad')
    op.drop_index(op.f('ix_ad_group_campaign_id'), table_name='ad_group')
    op.drop_table('ad_group')
    op.drop_index(op.f('ix_campaign_advertiser_id'), table_name='campaign')
    op.drop_table('campaign')
    op.drop_table('advertiser')
