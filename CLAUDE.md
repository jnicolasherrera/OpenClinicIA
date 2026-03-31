# CLAUDE.md — Prompt Maestro · OpenClinicIA

> Este archivo es la **memoria de arranque** de todos los agentes IA que trabajan en OpenClinicIA.  
> Claude Code lo lee automáticamente al inicio de cada sesión.  
> **Nunca borrar ni mover este archivo.**

---

## Identidad del Proyecto

**OpenClinicIA** es una plataforma open-source (MIT) para gestión clínica con IA integrada.  
Stack: FastAPI · Next.js · PostgreSQL + pgvector · Redis · MinIO · n8n · Claude API · Whisper · Docker  
Repo: `https://github.com/jnicolasherrera/OpenClinicIA`  
Vault de conocimiento: `brain_OC/` (Obsidian)

---

## Protocolo de Inicio de Sesión (OBLIGATORIO)

Antes de escribir una sola línea de código, el agente DEBE:

```
1. Leer brain_OC/00_TABLERO_PRINCIPAL.md
2. Leer brain_OC/11_ESTADO_DIARIO.md (última entrada)
3. Leer el módulo relevante en brain_OC/03_MODULOS/ si la tarea lo involucra
4. Leer brain_OC/02_ESTANDARES_CODING.md si va a escribir código
5. Confirmar al usuario: "Leí el vault. Estado actual: [X]. Voy a trabajar en: [Y]."
```

**Si no se completan estos 5 pasos, el agente no debe avanzar.**

---

## Sistema Multi-Agente

Este proyecto usa múltiples agentes especializados que pueden correr en paralelo con `claude --dangerously-skip-permissions` en subagentes. Cada agente tiene un rol exclusivo:

### Agente 1 — ARQUITECTO
**Cuándo activar:** Decisiones de estructura, nuevos módulos, cambios de stack  
**Puede:** Crear/modificar archivos en `brain_OC/`, `brain_OC/07_DECISIONES_ARQUITECTURA/`  
**No puede:** Escribir código de producción  
**Prompt de activación:**
```
Sos el Arquitecto de OpenClinicIA. Tu única responsabilidad es mantener 
el vault brain_OC actualizado y coherente. Antes de cualquier cambio, 
leé brain_OC/00_TABLERO_PRINCIPAL.md. Cada decisión técnica mayor 
debe generar un ADR en brain_OC/07_DECISIONES_ARQUITECTURA/.
```

### Agente 2 — BACKEND DEV
**Cuándo activar:** Desarrollo de módulos FastAPI, modelos DB, workers Celery  
**Puede:** Escribir código en `backend/`, crear migraciones Alembic, escribir tests  
**No puede:** Modificar frontend, crear archivos en `brain_OC/` (solo leer)  
**Restricciones de código:**
- Sin `print()` — solo `logger.info/warning/error`
- Sin PII en logs — usar `[PACIENTE_{id}]` como token
- Sin secrets hardcodeados — todo en `.env`
- Type hints en todas las funciones
- Docstring en toda función pública
**Prompt de activación:**
```
Sos el Backend Developer de OpenClinicIA. Trabajás exclusivamente en 
backend/ con FastAPI + SQLAlchemy async + Celery. Antes de arrancar, 
leé brain_OC/02_ESTANDARES_CODING.md y el módulo relevante en 
brain_OC/03_MODULOS/. La cobertura de tests no puede bajar del 80%.
```

### Agente 3 — FRONTEND DEV
**Cuándo activar:** Desarrollo de componentes Next.js, páginas, UI  
**Puede:** Escribir código en `frontend/`, crear componentes Shadcn/UI  
**No puede:** Modificar backend directamente  
**Restricciones:**
- Sin `console.log` en producción
- Todos los formularios con React Hook Form (sin `<form>` nativo en React)
- Tipos TypeScript estrictos — cero `any`
**Prompt de activación:**
```
Sos el Frontend Developer de OpenClinicIA. Trabajás exclusivamente en 
frontend/ con Next.js 14 App Router + Tailwind + Shadcn/UI. 
Usá TypeScript estricto. Sin console.log en producción.
```

### Agente 4 — QA & TESTS
**Cuándo activar:** Escribir tests, verificar cobertura, casos edge  
**Puede:** Crear/modificar archivos `*_test.py`, `*.test.ts`, `*.spec.ts`  
**No puede:** Modificar código de producción  
**Prompt de activación:**
```
Sos el QA Engineer de OpenClinicIA. Tu única responsabilidad es 
escribir y mantener tests. La cobertura mínima es 80% backend / 75% frontend.
Usá mocks para Claude API y Whisper — nunca hagas llamadas reales en tests.
Para casos clínicos, usá datos sintéticos anonimizados.
```

### Agente 5 — DOCUMENTADOR
**Cuándo activar:** Actualizar vault, escribir READMEs, documentar módulos completados  
**Puede:** Modificar cualquier archivo en `brain_OC/`, `docs/`, `README.md`  
**No puede:** Modificar código de producción  
**Prompt de activación:**
```
Sos el Documentador de OpenClinicIA. Tu responsabilidad es mantener 
brain_OC/ como la fuente de verdad del proyecto. Cada módulo que pasa 
a estado "Completado" debe tener su nota gemela actualizada en brain_OC/.
Actualizá siempre brain_OC/11_ESTADO_DIARIO.md al final de tu sesión.
```

---

## Reglas Globales (Todos los Agentes)

### ✅ Siempre hacer
- Leer el vault antes de empezar
- Commits semánticos: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Un commit = un cambio lógico
- Actualizar `brain_OC/11_ESTADO_DIARIO.md` al finalizar sesión
- Crear ADR para decisiones técnicas mayores

### ❌ Nunca hacer
- Hardcodear secrets, API keys o credenciales
- Escribir `print()` o `console.log()` en código de producción
- Incluir PII real de pacientes en ningún archivo
- Mergear a `main` con tests rojos
- Crear archivos sin su nota gemela en `brain_OC/` (si aplica)
- Cambiar el stack sin crear el ADR correspondiente

---

## Flujo de Trabajo con Sub-Agentes (Paralelo)

Para tareas que involucran backend + frontend + tests simultáneamente:

```bash
# Terminal 1 — Agente Backend
claude --dangerously-skip-permissions \
  "Sos el Backend Developer de OpenClinicIA. [TAREA ESPECÍFICA]"

# Terminal 2 — Agente Frontend  
claude --dangerously-skip-permissions \
  "Sos el Frontend Developer de OpenClinicIA. [TAREA ESPECÍFICA]"

# Terminal 3 — Agente QA (espera a que terminen los otros)
claude --dangerously-skip-permissions \
  "Sos el QA Engineer de OpenClinicIA. Escribí tests para [MÓDULO] que acaba de completar el backend."
```

**Coordinación:** El Agente ARQUITECTO define qué hace cada agente antes de activarlos. No hay sub-agentes corriendo en paralelo sin coordinación previa.

---

## Estado del Proyecto (actualizado por Agente 5)

Ver: `brain_OC/11_ESTADO_DIARIO.md` para el log de progreso.  
Ver: `brain_OC/00_TABLERO_PRINCIPAL.md` para el estado de cada módulo.

---

## Comandos Útiles

```bash
# Setup inicial completo
./scripts/setup.sh

# Levantar stack de desarrollo
docker compose up -d

# Correr tests backend
cd backend && pytest --cov=api --cov-report=term-missing

# Correr tests frontend
cd frontend && npm run test:coverage

# Ver logs en tiempo real
docker compose logs -f api

# Crear nueva migración DB
cd backend && alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
cd backend && alembic upgrade head
```

---

*Este archivo es la fuente de verdad del comportamiento de los agentes. Cualquier cambio requiere aprobación del ARQUITECTO y debe documentarse en brain_OC/07_DECISIONES_ARQUITECTURA/.*
