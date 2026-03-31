"""Initial schema — tenants, usuarios, pacientes, turnos, episodios

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# ---------------------------------------------------------------------------
# Metadatos de revisión
# ---------------------------------------------------------------------------
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extensiones PostgreSQL
    # ------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # pgvector es opcional: solo se instala si la extensión está disponible.
    # En entornos sin pgvector instalado esto no bloquea la migración.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION
            WHEN undefined_file THEN
                RAISE NOTICE 'pgvector no está instalado; se omite la extensión vector.';
        END;
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 2. Función auxiliar: current_tenant_id()
    #    Retorna el UUID del tenant activo desde la variable de sesión
    #    app.current_tenant_id. Si no está seteada devuelve NULL.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid
        LANGUAGE plpgsql STABLE
        AS $$
        DECLARE
            v_tenant_id text;
        BEGIN
            BEGIN
                v_tenant_id := current_setting('app.current_tenant_id', true);
            EXCEPTION
                WHEN undefined_object THEN
                    RETURN NULL;
            END;

            IF v_tenant_id IS NULL OR v_tenant_id = '' THEN
                RETURN NULL;
            END IF;

            RETURN v_tenant_id::uuid;
        END;
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 3. Función para trigger updated_at
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 4. Tabla: tenants
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "config",
            JSONB(),
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    # ------------------------------------------------------------------
    # 5. Tabla: usuarios
    # ------------------------------------------------------------------
    op.create_table(
        "usuarios",
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
            sa.ForeignKey("tenants.id", ondelete="CASCADE", name="fk_usuarios_tenant"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=True),
        sa.Column("apellido", sa.String(100), nullable=True),
        sa.Column("rol", sa.String(50), nullable=False, server_default="recepcion"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
        sa.CheckConstraint(
            "rol IN ('medico','recepcion','admin','paciente')",
            name="ck_usuarios_rol",
        ),
    )
    op.create_index("ix_usuarios_tenant_email", "usuarios", ["tenant_id", "email"])
    op.create_index("ix_usuarios_tenant_rol", "usuarios", ["tenant_id", "rol"])

    # ------------------------------------------------------------------
    # 6. Tabla: pacientes
    # ------------------------------------------------------------------
    op.create_table(
        "pacientes",
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
            sa.ForeignKey("tenants.id", ondelete="CASCADE", name="fk_pacientes_tenant"),
            nullable=False,
        ),
        sa.Column("numero_historia", sa.String(50), nullable=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellido", sa.String(100), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("dni", sa.String(20), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("obra_social", sa.String(200), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "dni", name="uq_pacientes_tenant_dni"),
        sa.UniqueConstraint(
            "tenant_id", "numero_historia", name="uq_pacientes_tenant_historia"
        ),
    )
    op.create_index("ix_pacientes_tenant_id", "pacientes", ["tenant_id"])

    # Índice GIN para búsqueda full-text en nombre y apellido
    op.execute(
        """
        CREATE INDEX ix_pacientes_nombre_apellido_gin
        ON pacientes
        USING gin(
            (to_tsvector('spanish', coalesce(nombre, '') || ' ' || coalesce(apellido, '')))
        )
        """
    )
    # Índice trigram para búsqueda parcial (ILIKE / similar_to)
    op.execute(
        """
        CREATE INDEX ix_pacientes_nombre_trgm
        ON pacientes
        USING gin(nombre gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_pacientes_apellido_trgm
        ON pacientes
        USING gin(apellido gin_trgm_ops)
        """
    )

    # ------------------------------------------------------------------
    # 7. Tabla: turnos
    # ------------------------------------------------------------------
    op.create_table(
        "turnos",
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
            sa.ForeignKey("tenants.id", ondelete="CASCADE", name="fk_turnos_tenant"),
            nullable=False,
        ),
        sa.Column(
            "paciente_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "pacientes.id", ondelete="RESTRICT", name="fk_turnos_paciente"
            ),
            nullable=False,
        ),
        sa.Column(
            "medico_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "usuarios.id", ondelete="RESTRICT", name="fk_turnos_medico"
            ),
            nullable=False,
        ),
        sa.Column(
            "fecha_hora", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column(
            "duracion_minutos", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column(
            "estado",
            sa.String(50),
            nullable=False,
            server_default="programado",
        ),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "sala_espera_ingreso", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "estado IN ('programado','confirmado','en_sala','en_atencion',"
            "'completado','cancelado','ausente')",
            name="ck_turnos_estado",
        ),
    )
    op.create_index(
        "ix_turnos_tenant_fecha_hora", "turnos", ["tenant_id", "fecha_hora"]
    )
    op.create_index(
        "ix_turnos_medico_fecha_hora", "turnos", ["medico_id", "fecha_hora"]
    )
    op.create_index("ix_turnos_tenant_estado", "turnos", ["tenant_id", "estado"])

    # ------------------------------------------------------------------
    # 8. Tabla: episodios
    # ------------------------------------------------------------------
    op.create_table(
        "episodios",
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
            sa.ForeignKey(
                "tenants.id", ondelete="CASCADE", name="fk_episodios_tenant"
            ),
            nullable=False,
        ),
        sa.Column(
            "paciente_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "pacientes.id", ondelete="RESTRICT", name="fk_episodios_paciente"
            ),
            nullable=False,
        ),
        sa.Column(
            "turno_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "turnos.id", ondelete="SET NULL", name="fk_episodios_turno"
            ),
            nullable=True,
        ),
        sa.Column(
            "medico_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "usuarios.id", ondelete="RESTRICT", name="fk_episodios_medico"
            ),
            nullable=False,
        ),
        sa.Column(
            "fecha",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("motivo_consulta", sa.Text(), nullable=False),
        sa.Column("anamnesis", sa.Text(), nullable=True),
        sa.Column("examen_fisico", sa.Text(), nullable=True),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("plan_terapeutico", sa.Text(), nullable=True),
        sa.Column("soap_subjetivo", sa.Text(), nullable=True),
        sa.Column("soap_objetivo", sa.Text(), nullable=True),
        sa.Column("soap_assessment", sa.Text(), nullable=True),
        sa.Column("soap_plan", sa.Text(), nullable=True),
        sa.Column("transcripcion_raw", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_episodios_paciente_fecha", "episodios", ["paciente_id", "fecha"]
    )
    op.create_index(
        "ix_episodios_tenant_fecha", "episodios", ["tenant_id", "fecha"]
    )

    # ------------------------------------------------------------------
    # 9. Triggers updated_at en todas las tablas
    # ------------------------------------------------------------------
    for table in ("tenants", "usuarios", "pacientes", "turnos", "episodios"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            """
        )

    # ------------------------------------------------------------------
    # 10. Row Level Security (RLS)
    # ------------------------------------------------------------------
    for table in ("tenants", "usuarios", "pacientes", "turnos", "episodios"):
        # Activar RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Política principal: el tenant_id de la fila debe coincidir con el
        # tenant activo en la sesión PostgreSQL.
        #
        # Para tenants la comparación es directamente contra el id de la fila,
        # ya que la tabla no tiene columna tenant_id propia.
        if table == "tenants":
            using_clause = "id = current_tenant_id()"
        else:
            using_clause = "tenant_id = current_tenant_id()"

        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING ({using_clause})
            WITH CHECK ({using_clause})
            """
        )

        # Política de bypass para superuser / rol de servicio backend
        # (el rol de la aplicación debe ser el propietario de las tablas
        # o tener BYPASSRLS; esta policy sirve para roles intermedios).
        op.execute(
            f"""
            CREATE POLICY superuser_bypass_policy ON {table}
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (current_setting('app.bypass_rls', true) = 'on')
            WITH CHECK (current_setting('app.bypass_rls', true) = 'on')
            """
        )


# ---------------------------------------------------------------------------
# DOWNGRADE — elimina todo en orden inverso para respetar FK
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Deshabilitar RLS y eliminar políticas antes de hacer DROP TABLE
    for table in ("episodios", "turnos", "pacientes", "usuarios", "tenants"):
        op.execute(f"DROP POLICY IF EXISTS superuser_bypass_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Eliminar tablas en orden inverso de dependencias
    op.drop_table("episodios")
    op.drop_table("turnos")
    op.drop_table("pacientes")
    op.drop_table("usuarios")
    op.drop_table("tenants")

    # Eliminar funciones auxiliares
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id() CASCADE")
