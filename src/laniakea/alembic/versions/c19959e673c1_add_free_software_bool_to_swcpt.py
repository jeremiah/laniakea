"""Add free software bool to swcpt

Revision ID: c19959e673c1
Revises: 9a217b14748d
Create Date: 2020-01-19 02:06:56.023590

"""
# flake8: noqa

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c19959e673c1'
down_revision = '9a217b14748d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('archive_sw_components', sa.Column('is_free', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('archive_sw_components', 'is_free')
    # ### end Alembic commands ###
