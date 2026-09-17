"""add maintenance tracker tables

Revision ID: 1fb5c769516c
Revises: d906cdd1b7ee
Create Date: 2026-09-16 14:01:10.650635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fb5c769516c'
down_revision: Union[str, None] = 'd906cdd1b7ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create maintenance_parts table
    op.create_table('maintenance_parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('default_interval_km', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_parts_id'), 'maintenance_parts', ['id'], unique=False)

    # Create maintenance_brands table
    op.create_table('maintenance_brands',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('part_id', sa.Integer(), nullable=False),
    sa.Column('brand_name', sa.String(), nullable=False),
    sa.Column('interval_km', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['part_id'], ['maintenance_parts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_brands_id'), 'maintenance_brands', ['id'], unique=False)

    # Create car_maintenance table
    op.create_table('car_maintenance',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('car_id', sa.Integer(), nullable=False),
    sa.Column('part_id', sa.Integer(), nullable=False),
    sa.Column('last_changed_km', sa.Integer(), nullable=True),
    sa.Column('last_changed_brand_id', sa.Integer(), nullable=True),
    sa.Column('last_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_change_km', sa.Integer(), nullable=True),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['last_changed_brand_id'], ['maintenance_brands.id'], ),
    sa.ForeignKeyConstraint(['part_id'], ['maintenance_parts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_car_maintenance_id'), 'car_maintenance', ['id'], unique=False)

    # Add new columns to cars
    op.add_column('cars', sa.Column('current_km', sa.Integer(), nullable=True))
    op.add_column('cars', sa.Column('estimated_km_per_month', sa.Integer(), nullable=True))
    op.add_column('cars', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))


def downgrade() -> None:
    op.drop_column('cars', 'created_at')
    op.drop_column('cars', 'estimated_km_per_month')
    op.drop_column('cars', 'current_km')
    op.drop_index(op.f('ix_car_maintenance_id'), table_name='car_maintenance')
    op.drop_table('car_maintenance')
    op.drop_index(op.f('ix_maintenance_brands_id'), table_name='maintenance_brands')
    op.drop_table('maintenance_brands')
    op.drop_index(op.f('ix_maintenance_parts_id'), table_name='maintenance_parts')
    op.drop_table('maintenance_parts')