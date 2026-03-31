-- OpenClinicIA — Inicialización DB
-- Este script corre automáticamente al levantar el contenedor PostgreSQL

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- búsqueda full-text

-- Schema de auditoría
CREATE SCHEMA IF NOT EXISTS audit;

-- Función para updated_at automático
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función para RLS: obtener tenant_id del contexto
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
BEGIN
  RETURN current_setting('app.tenant_id', true)::UUID;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ──────────────────────────────────────────────
-- Tabla: tenants (clínicas / consultorios)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    plan        TEXT NOT NULL DEFAULT 'mvp',  -- mvp | pro | enterprise
    activo      BOOLEAN DEFAULT TRUE,
    config      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Tabla: usuarios
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    apellido        TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'recepcion',
                    -- admin | medico | recepcion | paciente
    especialidad    TEXT,  -- solo para rol=medico
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_usuarios ON usuarios
    USING (tenant_id = current_tenant_id());

-- ──────────────────────────────────────────────
-- Tabla: pacientes
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pacientes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre                  TEXT NOT NULL,
    apellido                TEXT NOT NULL,
    fecha_nacimiento        DATE,
    documento               TEXT,
    tipo_documento          TEXT DEFAULT 'DNI',
    email                   TEXT,
    telefono                TEXT,
    cobertura_id            UUID,
    numero_afiliado         TEXT,
    consentimiento_grabacion BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE pacientes ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_pacientes ON pacientes
    USING (tenant_id = current_tenant_id());

-- ──────────────────────────────────────────────
-- Tabla: turnos
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turnos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    paciente_id     UUID NOT NULL REFERENCES pacientes(id),
    medico_id       UUID NOT NULL REFERENCES usuarios(id),
    fecha_hora      TIMESTAMPTZ NOT NULL,
    duracion_min    INTEGER NOT NULL DEFAULT 15,
    estado          TEXT NOT NULL DEFAULT 'AGENDADO',
                    -- AGENDADO | EN_ESPERA | EN_CONSULTORIO | FINALIZADO | CANCELADO
    motivo_consulta TEXT,
    confirmado      BOOLEAN DEFAULT FALSE,
    clasificacion_triaje TEXT,  -- GUARDIA_INMEDIATA | URGENTE_24H | RUTINA
    resumen_triaje  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE turnos ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_turnos ON turnos
    USING (tenant_id = current_tenant_id());

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_turnos_medico_fecha ON turnos(medico_id, fecha_hora);
CREATE INDEX IF NOT EXISTS idx_turnos_estado ON turnos(tenant_id, estado);

-- ──────────────────────────────────────────────
-- Tabla: episodios_clinicos
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS episodios_clinicos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    turno_id        UUID REFERENCES turnos(id),
    paciente_id     UUID NOT NULL REFERENCES pacientes(id),
    medico_id       UUID NOT NULL REFERENCES usuarios(id),
    estado          TEXT NOT NULL DEFAULT 'ABIERTO',
                    -- ABIERTO | FIRMADO | CERRADO
    soap            JSONB,  -- {subjetivo, objetivo, analisis, plan}
    codigos_cie10   TEXT[],
    consentimiento_verificado BOOLEAN DEFAULT FALSE,
    firmado_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE episodios_clinicos ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_episodios ON episodios_clinicos
    USING (tenant_id = current_tenant_id());

-- ──────────────────────────────────────────────
-- Tabla: episodios_embedding (RAG)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS episodios_embedding (
    id              UUID PRIMARY KEY REFERENCES episodios_clinicos(id),
    tenant_id       UUID NOT NULL,
    embedding       vector(1536),
    especialidad    TEXT,
    score_edicion   FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para búsqueda vectorial eficiente
CREATE INDEX IF NOT EXISTS idx_episodios_embedding_hnsw
    ON episodios_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ──────────────────────────────────────────────
-- Tabla: audit_logs (INSERT-ONLY — nunca UPDATE/DELETE)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    usuario_id  UUID,
    accion      TEXT NOT NULL,  -- READ | CREATE | UPDATE | DELETE
    tabla       TEXT NOT NULL,
    registro_id UUID,
    payload     JSONB,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Solo INSERT permitido en audit_logs
REVOKE UPDATE, DELETE ON audit.logs FROM PUBLIC;

-- ──────────────────────────────────────────────
-- Triggers de updated_at
-- ──────────────────────────────────────────────
CREATE TRIGGER set_updated_at_tenants
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at_usuarios
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at_pacientes
    BEFORE UPDATE ON pacientes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at_turnos
    BEFORE UPDATE ON turnos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at_episodios
    BEFORE UPDATE ON episodios_clinicos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ──────────────────────────────────────────────
-- Tenant y usuario admin de ejemplo (solo desarrollo)
-- ──────────────────────────────────────────────
INSERT INTO tenants (id, nombre, slug, plan)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Clínica Demo',
    'clinica-demo',
    'mvp'
) ON CONFLICT (slug) DO NOTHING;
