"""MOD_05 Facturacion — obras_sociales, comprobantes, items_comprobante

Revision ID: 002_facturacion
Revises: 001_initial_schema
Create Date: 2026-03-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = "002_facturacion"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crea las tablas obras_sociales, comprobantes e items_comprobante con RLS."""

    # ------------------------------------------------------------------
    # 1. Tabla obras_sociales
    # ------------------------------------------------------------------
    op.create_table(
        "obras_sociales",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("plan", sa.String(100), nullable=True),
        sa.Column("porcentaje_cobertura", sa.Float(), nullable=False, server_default="0"),
        sa.Column("copago_consulta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_obras_sociales_tenant_codigo"),
    )
    op.create_index(
        "ix_obras_sociales_tenant_activa",
        "obras_sociales",
        ["tenant_id", "activa"],
    )

    # ------------------------------------------------------------------
    # 2. Tabla comprobantes
    # ------------------------------------------------------------------
    op.create_table(
        "comprobantes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "turno_id",
            UUID(as_uuid=True),
            sa.ForeignKey("turnos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "paciente_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pacientes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "obra_social_id",
            UUID(as_uuid=True),
            sa.ForeignKey("obras_sociales.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("numero_comprobante", sa.String(50), nullable=False),
        sa.Column(
            "tipo",
            sa.String(20),
            sa.CheckConstraint(
                "tipo IN ('factura_a','factura_b','recibo','orden')",
                name="ck_comprobantes_tipo",
            ),
            nullable=False,
            server_default="recibo",
        ),
        sa.Column(
            "fecha_emision",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("monto_total", sa.Float(), nullable=False),
        sa.Column("monto_cobertura", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monto_copago", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monto_particular", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "estado",
            sa.String(30),
            sa.CheckConstraint(
                "estado IN ('pendiente','pagado','cancelado','anulado')",
                name="ck_comprobantes_estado",
            ),
            nullable=False,
            server_default="pendiente",
        ),
        sa.Column("concepto", sa.String(500), nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "tenant_id", "numero_comprobante", name="uq_comprobantes_tenant_numero"
        ),
    )
    op.create_index(
        "ix_comprobantes_paciente_fecha",
        "comprobantes",
        ["paciente_id", "fecha_emision"],
    )
    op.create_index(
        "ix_comprobantes_tenant_estado",
        "comprobantes",
        ["tenant_id", "estado"],
    )
    op.create_index(
        "ix_comprobantes_turno_id",
        "comprobantes",
        ["turno_id"],
    )

    # ------------------------------------------------------------------
    # 3. Tabla items_comprobante
    # ------------------------------------------------------------------
    op.create_table(
        "items_comprobante",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "comprobante_id",
            UUID(as_uuid=True),
            sa.ForeignKey("comprobantes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("descripcion", sa.String(300), nullable=False),
        sa.Column("cantidad", sa.Float(), nullable=False, server_default="1"),
        sa.Column("precio_unitario", sa.Float(), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_items_comprobante_comprobante_id",
        "items_comprobante",
        ["comprobante_id"],
    )

    # ------------------------------------------------------------------
    # 4. Trigger updated_at en obras_sociales y comprobantes
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_obras_sociales_updated_at
        BEFORE UPDATE ON obras_sociales
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_comprobantes_updated_at
        BEFORE UPDATE ON comprobantes
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # 5. Row-Level Security (RLS) con política tenant_isolation_policy
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE obras_sociales ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON obras_sociales
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )

    op.execute("ALTER TABLE comprobantes ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON comprobantes
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    """Elimina las tablas en orden inverso respetando las FK."""
    # RLS
    op.execute("ALTER TABLE comprobantes DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON comprobantes;")
    op.execute("ALTER TABLE obras_sociales DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON obras_sociales;")

    # Triggers
    op.execute("DROP TRIGGER IF EXISTS trg_comprobantes_updated_at ON comprobantes;")
    op.execute("DROP TRIGGER IF EXISTS trg_obras_sociales_updated_at ON obras_sociales;")

    # Tablas (orden: dependientes primero)
    op.drop_table("items_comprobante")
    op.drop_table("comprobantes")
    op.drop_table("obras_sociales")

    # Función auxiliar (solo si no la usa nadie más)
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE;")
