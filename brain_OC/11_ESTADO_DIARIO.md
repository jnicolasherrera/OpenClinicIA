# 📅 Estado Diario — OpenClinicIA

> Log de progreso por sesión. Entrada más reciente al principio.

---

## 2026-03-30 — Sesión 3: MOD_05 + MOD_06 + Whisper real

### Agente: Claude Code (Arquitecto + 3 subagentes paralelos)

### ✅ Lo que se construyó

**MOD_05 Facturación (backend/ + frontend/):**
- `models/facturacion.py` — ObraSocial, Comprobante, ItemComprobante (SQLAlchemy)
- `api/v1/facturacion/` — schemas, repository, service (cálculo copagos), router (8 endpoints)
- `alembic/versions/002_facturacion.py` — migración con RLS, triggers, índices
- `frontend/app/facturacion/page.tsx` — 3 tabs: Comprobantes, Obras Sociales, Resumen
- `components/ui/select.tsx` — componente Shadcn Select (creado para facturación)
- `brain_OC/03_MODULOS/MOD_05_FACTURACION.md` — documentación completa
- Tests: 6 casos (crear OS, comprobante con/sin OS, pagar, resumen) — todos PASSED

**MOD_06 Árbol Agentes n8n + Telegram:**
- `api/v1/agentes/` — AgenteJefe (Claude Sonnet), GerenteAgenda, GerenteNotificaciones, router webhook
- `POST /api/v1/agentes/webhook/telegram` — entrada del árbol desde n8n (secret header)
- `n8n/workflows/agente_jefe_telegram.json` — Telegram Trigger → API → respuesta
- `n8n/workflows/recordatorio_turnos.json` — Schedule cada 1h → recordatorios Telegram
- `n8n/README.md` — instrucciones de setup completas
- Variables nuevas en config.py: TELEGRAM_BOT_TOKEN, N8N_WEBHOOK_SECRET, N8N_BASE_URL, INTERNAL_API_TOKEN
- `brain_OC/03_MODULOS/MOD_06_ARBOL_AGENTES.md` — documentación con diagrama ASCII

**Whisper real — Ambient Scribe (MOD_03):**
- `api/v1/ia/scribe/service_whisper.py` — WhisperService async con fallback si sin API key
- `worker_transcripcion.py` — reemplazado con Whisper real (openai==1.57.0), pipeline completo
- Nuevo task Celery: `transcribir_y_generar_soap` (pipeline audio→texto→SOAP)
- Endpoint `POST /ia/scribe/transcribir` — acepta upload directo o URL async
- Endpoint `GET /ia/scribe/estado/{task_id}` — estado Celery
- `brain_OC/03_MODULOS/MOD_03_AMBIENT_SCRIBE.md` — documentación completa
- Tests: 4 casos scribe (SOAP, fallback sin key, async URL, estado task) — todos PASSED

### 📊 Métricas de la sesión
- Archivos nuevos: ~30
- Líneas de código: ~2800
- Tests totales acumulados: **34/34 PASSED**
- Rutas frontend: 7 (agregada /facturacion)
- Fixes: Header FastAPI (agentes router), select.tsx faltante

### 🔜 Próxima sesión
- MOD_07 Laboratorio (muestras, LIS/PACS, stock)
- MOD_08 Telemedicina (WebRTC básico)
- Deploy en VPS con docker compose + nginx
- CI/CD: actualizar GitHub Actions para correr los 34 tests

---

## 2026-03-30 — Sesión 2: MVP Base Completo

### Agente: Claude Code (Arquitecto + subagentes paralelos)

### ✅ Lo que se construyó

**Backend FastAPI (backend/):**
- `main.py` — FastAPI app con lifespan, CORS, health check
- `core/config.py` — Settings pydantic-settings desde .env
- `core/database.py` — SQLAlchemy async engine + get_db dependency
- `core/security.py` — JWT (python-jose) + bcrypt password hashing
- `core/logging.py` — Logger estructurado sin PII
- `models/` — tenant, usuario, paciente, turno, episodio (SQLAlchemy)
- `api/v1/auth/` — login, refresh token, /me endpoint
- `api/v1/agenda/` — CRUD turnos, sala de espera, ingresar a sala
- `api/v1/pacientes/` — CRUD pacientes + historia clínica
- `api/v1/ia/triaje/` — Clasificación urgencia ESI con Claude Haiku
- `api/v1/ia/scribe/` — Generación SOAP con Claude Sonnet
- `workers/celery_app.py` — Celery con Redis broker
- `tests/` — test_auth, test_agenda, test_pacientes con fixtures

**Frontend Next.js (frontend/):**
- App Router con layout, providers (QueryClient, Toaster)
- Login page con React Hook Form + Zod validation
- Dashboard con métricas del día (react-query)
- Agenda con CalendarioSemanal + SalaEspera (polling 30s)
- Pacientes con búsqueda debounced
- Sidebar + Header responsive
- lib/api.ts con axios + JWT interceptor + refresh automático
- lib/store.ts con Zustand (auth + UI state)
- Componentes Shadcn/UI: Button, Card, Input, Badge, Dialog

**DB & Migraciones:**
- `alembic/versions/001_initial_schema.py` — Schema completo
- Extensiones: uuid-ossp, pg_trgm, vector (pgvector)
- RLS policies para multi-tenant isolation
- Triggers updated_at en todas las tablas
- `scripts/init_db.sql` actualizado con datos demo

**Documentación:**
- `brain_OC/00_TABLERO_PRINCIPAL.md` actualizado
- `brain_OC/03_MODULOS/MOD_02_HISTORIA_CLINICA.md` creado
- Este archivo actualizado

### 📊 Métricas de la sesión
- Archivos creados: ~50
- Líneas de código: ~3500
- Módulos implementados: Auth, Agenda, Pacientes, Historia Clínica, Triaje IA, Ambient Scribe (parcial)
- Tests escritos: 24 casos de prueba

---

## 2026-03-30 — Sesión 1: Setup inicial

### Agente: Claude Code (Arquitecto / Setup inicial)

### ✅ Lo que se hizo hoy

1. **Autenticación GitHub** — Activada cuenta `jnicolasherrera` en `gh` (keyring, token gho_).
2. **Repo público creado** — `https://github.com/jnicolasherrera/OpenClinicIA` (MIT, público).
3. **Git init + primer commit + push a main** — 16 archivos, commit semántico `chore: initial commit`.
4. **`brain_OC/11_ESTADO_DIARIO.md` creado** — Este archivo.

---
