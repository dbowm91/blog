"""merge_multiple_heads

Revision ID: 82ce77695033
Revises: 16034e1c5a45, add_perf_indexes, add_totp_secret_to_user
Create Date: 2026-05-02 21:34:52.570197

"""

# revision identifiers, used by Alembic.
revision = "82ce77695033"
down_revision = ("16034e1c5a45", "add_perf_indexes", "add_totp_secret_to_user")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
