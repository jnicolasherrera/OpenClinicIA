-- =============================================================================
-- OpenClinicIA — Script de inicialización de base de datos (desarrollo)
-- =============================================================================
-- Uso:
--   psql -U postgres -f scripts/init_db.sql
--
-- ADVERTENCIA: Este script crea la base de datos y un tenant de demo.
-- NO usar en producción sin limpiar las credenciales de muestra.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Crear la base de datos (ejecutar como superusuario de PostgreSQL)
-- -----------------------------------------------------------------------------
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'openclinica_dev'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS openclinica_dev;
CREATE DATABASE openclinica_dev
    WITH
    OWNER     = postgres
    ENCODING  = 'UTF8'
    CONNECTION LIMIT = -1;

\c openclinica_dev

-- -----------------------------------------------------------------------------
-- 1. Extensiones
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- pgvector: requiere que el paquete postgresql-pgvector esté instalado
-- en el sistema operativo (ej: apt install postgresql-16-pgvector).
-- Si no está disponible, comentar o eliminar la línea siguiente.
-- CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- 2. Funciones auxiliares
-- -----------------------------------------------------------------------------

-- Retorna el UUID del tenant activo desde la variable de sesión PostgreSQL.
-- La variable se setea con: SET LOCAL app.current_tenant_id = '<uuid>';
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

-- Función genérica para triggers de updated_at.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- 3. Tabla: tenants
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      VARCHAR(200) NOT NULL,
    slug        VARCHAR(100) NOT NULL,
    plan        VARCHAR(50)  NOT NULL DEFAULT 'free',
    activo      BOOLEAN      NOT NULL DEFAULT TRUE,
    config      JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenants_slug UNIQUE (slug)
);

-- -----------------------------------------------------------------------------
-- 4. Tabla: usuarios
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL
                                  REFERENCES tenants(id) ON DELETE CASCADE,
    email            VARCHAR(255) NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    nombre           VARCHAR(100),
    apellido         VARCHAR(100),
    rol              VARCHAR(50)  NOT NULL DEFAULT 'recepcion',
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT ck_usuarios_rol   CHECK (rol IN ('medico','recepcion','admin','paciente'))
);

CREATE INDEX IF NOT EXISTS ix_usuarios_tenant_email ON usuarios(tenant_id, email);
CREATE INDEX IF NOT EXISTS ix_usuarios_tenant_rol   ON usuarios(tenant_id, rol);

-- -----------------------------------------------------------------------------
-- 5. Tabla: pacientes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pacientes (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL
                                  REFERENCES tenants(id) ON DELETE CASCADE,
    numero_historia  VARCHAR(50),
    nombre           VARCHAR(100) NOT NULL,
    apellido         VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    dni              VARCHAR(20),
    telefono         VARCHAR(20),
    email            VARCHAR(255),
    obra_social      VARCHAR(200),
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_pacientes_tenant_dni      UNIQUE (tenant_id, dni),
    CONSTRAINT uq_pacientes_tenant_historia UNIQUE (tenant_id, numero_historia)
);

CREATE INDEX IF NOT EXISTS ix_pacientes_tenant_id ON pacientes(tenant_id);

-- Índice GIN full-text para búsqueda de pacientes por nombre+apellido
CREATE INDEX IF NOT EXISTS ix_pacientes_nombre_apellido_gin
    ON pacientes
    USING gin(
        to_tsvector('spanish',
            coalesce(nombre, '') || ' ' || coalesce(apellido, ''))
    );

-- Índices trigram para búsqueda parcial (ILIKE / similar_to)
CREATE INDEX IF NOT EXISTS ix_pacientes_nombre_trgm
    ON pacientes USING gin(nombre gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_pacientes_apellido_trgm
    ON pacientes USING gin(apellido gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- 6. Tabla: turnos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS turnos (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID         NOT NULL
                                      REFERENCES tenants(id) ON DELETE CASCADE,
    paciente_id          UUID         NOT NULL
                                      REFERENCES pacientes(id) ON DELETE RESTRICT,
    medico_id            UUID         NOT NULL
                                      REFERENCES usuarios(id) ON DELETE RESTRICT,
    fecha_hora           TIMESTAMPTZ  NOT NULL,
    duracion_minutos     INTEGER      NOT NULL DEFAULT 30,
    estado               VARCHAR(50)  NOT NULL DEFAULT 'programado',
    motivo               VARCHAR(500),
    notas                TEXT,
    sala_espera_ingreso  TIMESTAMPTZ,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_turnos_estado CHECK (
        estado IN ('programado','confirmado','en_sala','en_atencion',
                   'completado','cancelado','ausente')
    )
);

CREATE INDEX IF NOT EXISTS ix_turnos_tenant_fecha_hora ON turnos(tenant_id, fecha_hora);
CREATE INDEX IF NOT EXISTS ix_turnos_medico_fecha_hora ON turnos(medico_id, fecha_hora);
CREATE INDEX IF NOT EXISTS ix_turnos_tenant_estado     ON turnos(tenant_id, estado);

-- -----------------------------------------------------------------------------
-- 7. Tabla: episodios
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS episodios (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID        NOT NULL
                                  REFERENCES tenants(id) ON DELETE CASCADE,
    paciente_id       UUID        NOT NULL
                                  REFERENCES pacientes(id) ON DELETE RESTRICT,
    turno_id          UUID
                                  REFERENCES turnos(id) ON DELETE SET NULL,
    medico_id         UUID        NOT NULL
                                  REFERENCES usuarios(id) ON DELETE RESTRICT,
    fecha             TIMESTAMPTZ NOT NULL DEFAULT now(),
    motivo_consulta   TEXT        NOT NULL,
    anamnesis         TEXT,
    examen_fisico     TEXT,
    diagnostico       TEXT,
    plan_terapeutico  TEXT,
    soap_subjetivo    TEXT,
    soap_objetivo     TEXT,
    soap_assessment   TEXT,
    soap_plan         TEXT,
    transcripcion_raw TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_episodios_paciente_fecha ON episodios(paciente_id, fecha);
CREATE INDEX IF NOT EXISTS ix_episodios_tenant_fecha   ON episodios(tenant_id, fecha);

-- -----------------------------------------------------------------------------
-- 8. Triggers updated_at
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_pacientes_updated_at
    BEFORE UPDATE ON pacientes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_turnos_updated_at
    BEFORE UPDATE ON turnos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_episodios_updated_at
    BEFORE UPDATE ON episodios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- 9. Row Level Security (RLS)
-- -----------------------------------------------------------------------------
ALTER TABLE tenants   ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios  ENABLE ROW LEVEL SECURITY;
ALTER TABLE pacientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE turnos    ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodios ENABLE ROW LEVEL SECURITY;

-- Política de aislamiento por tenant
CREATE POLICY tenant_isolation_policy ON tenants
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (id = current_tenant_id())
    WITH CHECK (id = current_tenant_id());

CREATE POLICY tenant_isolation_policy ON usuarios
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_policy ON pacientes
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_policy ON turnos
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_policy ON episodios
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Política de bypass para el rol de servicio del backend.
-- Se activa con: SET LOCAL app.bypass_rls = 'on';
CREATE POLICY superuser_bypass_policy ON tenants
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (current_setting('app.bypass_rls', true) = 'on');

CREATE POLICY superuser_bypass_policy ON usuarios
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (current_setting('app.bypass_rls', true) = 'on');

CREATE POLICY superuser_bypass_policy ON pacientes
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (current_setting('app.bypass_rls', true) = 'on');

CREATE POLICY superuser_bypass_policy ON turnos
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (current_setting('app.bypass_rls', true) = 'on');

CREATE POLICY superuser_bypass_policy ON episodios
    AS PERMISSIVE FOR ALL TO PUBLIC
    USING (current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (current_setting('app.bypass_rls', true) = 'on');

-- =============================================================================
-- DATOS DE DEMO
-- Todos los INSERTs hacen bypass de RLS mediante SET LOCAL.
-- Contraseña de todos los usuarios demo: Demo1234!
-- Hash bcrypt cost=12 generado con Python: bcrypt.hashpw(b'Demo1234!', bcrypt.gensalt(12))
-- =============================================================================
BEGIN;
SET LOCAL app.bypass_rls = 'on';

-- -----------------------------------------------------------------------------
-- Tenant de demo
-- -----------------------------------------------------------------------------
INSERT INTO tenants (id, nombre, slug, plan, activo, config)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Clínica Demo OpenClinicIA',
    'demo',
    'pro',
    TRUE,
    '{
        "timezone": "America/Argentina/Buenos_Aires",
        "idioma": "es",
        "moneda": "ARS",
        "modulos": ["turnos", "episodios", "ia_transcripcion"]
    }'::jsonb
)
ON CONFLICT (slug) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Usuario admin de demo  —  admin@demo.com / Demo1234!
-- -----------------------------------------------------------------------------
INSERT INTO usuarios (id, tenant_id, email, hashed_password, nombre, apellido, rol, activo)
VALUES (
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    'admin@demo.com',
    '$2b$12$jxjuO4f9nj9/caD9RkbBvehr52wqQe1cMeSXfvaTU1BOA2cdOCLnq',
    'Admin',
    'Demo',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Usuario médico de demo  —  medico@demo.com / Demo1234!
-- -----------------------------------------------------------------------------
INSERT INTO usuarios (id, tenant_id, email, hashed_password, nombre, apellido, rol, activo)
VALUES (
    '00000000-0000-0000-0000-000000000011',
    '00000000-0000-0000-0000-000000000001',
    'medico@demo.com',
    '$2b$12$jxjuO4f9nj9/caD9RkbBvehr52wqQe1cMeSXfvaTU1BOA2cdOCLnq',
    'Juan',
    'García',
    'medico',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 5 Pacientes ficticios de prueba (datos completamente inventados)
-- -----------------------------------------------------------------------------
INSERT INTO pacientes
    (id, tenant_id, numero_historia, nombre, apellido,
     fecha_nacimiento, dni, telefono, email, obra_social, activo)
VALUES
    (
        '00000000-0000-0000-0001-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'HC-00001',
        'María', 'González',
        '1985-04-12',
        '11111111',
        '011-4521-3344',
        'maria.gonzalez.demo@example.com',
        'OSDE',
        TRUE
    ),
    (
        '00000000-0000-0000-0001-000000000002',
        '00000000-0000-0000-0000-000000000001',
        'HC-00002',
        'Carlos', 'Rodríguez',
        '1972-09-28',
        '22222222',
        '011-4833-9901',
        'carlos.rodriguez.demo@example.com',
        'Swiss Medical',
        TRUE
    ),
    (
        '00000000-0000-0000-0001-000000000003',
        '00000000-0000-0000-0000-000000000001',
        'HC-00003',
        'Ana', 'Martínez',
        '1990-01-07',
        '33333333',
        '011-4712-0056',
        'ana.martinez.demo@example.com',
        'Galeno',
        TRUE
    ),
    (
        '00000000-0000-0000-0001-000000000004',
        '00000000-0000-0000-0000-000000000001',
        'HC-00004',
        'Luis', 'Fernández',
        '1965-11-15',
        '44444444',
        '011-4944-7722',
        NULL,
        'IOMA',
        TRUE
    ),
    (
        '00000000-0000-0000-0001-000000000005',
        '00000000-0000-0000-0000-000000000001',
        'HC-00005',
        'Sofía', 'López',
        '2001-06-30',
        '55555555',
        '011-4600-1234',
        'sofia.lopez.demo@example.com',
        NULL,
        TRUE
    )
ON CONFLICT (tenant_id, dni) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3 Turnos de ejemplo (hoy y mañana, calculados dinámicamente con now())
-- -----------------------------------------------------------------------------
INSERT INTO turnos
    (id, tenant_id, paciente_id, medico_id, fecha_hora,
     duracion_minutos, estado, motivo)
VALUES
    (
        '00000000-0000-0000-0002-000000000001',
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0001-000000000001',   -- María González
        '00000000-0000-0000-0000-000000000011',   -- Dr. Juan García
        date_trunc('day', now()) + interval '9 hours',
        30,
        'confirmado',
        'Control de presión arterial y glucemia'
    ),
    (
        '00000000-0000-0000-0002-000000000002',
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0001-000000000002',   -- Carlos Rodríguez
        '00000000-0000-0000-0000-000000000011',   -- Dr. Juan García
        date_trunc('day', now()) + interval '10 hours 30 minutes',
        45,
        'programado',
        'Consulta por dolor lumbar crónico'
    ),
    (
        '00000000-0000-0000-0002-000000000003',
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0001-000000000003',   -- Ana Martínez
        '00000000-0000-0000-0000-000000000011',   -- Dr. Juan García
        date_trunc('day', now()) + interval '1 day 9 hours',
        30,
        'programado',
        'Primera consulta — cefalea recurrente'
    )
ON CONFLICT DO NOTHING;

COMMIT;

-- -----------------------------------------------------------------------------
-- Resumen de datos insertados
-- -----------------------------------------------------------------------------
SELECT 'tenants'   AS tabla, count(*) AS filas FROM tenants
UNION ALL
SELECT 'usuarios'  AS tabla, count(*) AS filas FROM usuarios
UNION ALL
SELECT 'pacientes' AS tabla, count(*) AS filas FROM pacientes
UNION ALL
SELECT 'turnos'    AS tabla, count(*) AS filas FROM turnos
UNION ALL
SELECT 'episodios' AS tabla, count(*) AS filas FROM episodios
ORDER BY tabla;
