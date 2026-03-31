# MOD_05 — Facturación

## Descripción

El módulo de Facturación permite gestionar el ciclo económico de las consultas médicas: registro de obras sociales con sus coberturas, emisión de comprobantes (facturas, recibos, órdenes), cálculo automático de copagos y montos de cobertura, y generación de resúmenes de recaudación.

Soporta multi-tenant con aislamiento a nivel de base de datos (RLS + filtro por `tenant_id`).

---

## Modelos de datos

### ObraSocial (`obras_sociales`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador único |
| `tenant_id` | UUID FK → tenants | Tenant propietario |
| `nombre` | str(200) | Nombre de la obra social |
| `codigo` | str(50) | Código único por tenant (ej: "OSDE-210") |
| `plan` | str(100) nullable | Nombre del plan (ej: "210", "Bronce") |
| `porcentaje_cobertura` | float | Porcentaje que cubre la OS (0–100) |
| `copago_consulta` | float | Monto fijo de copago por consulta |
| `activa` | bool | Si está disponible para nuevos comprobantes |
| `notas` | text nullable | Observaciones libres |
| `created_at` / `updated_at` | timestamptz | Auditoría |

Constraint único: `(tenant_id, codigo)`.

### Comprobante (`comprobantes`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador único |
| `tenant_id` | UUID FK → tenants | Tenant propietario |
| `turno_id` | UUID FK → turnos nullable | Turno asociado (opcional) |
| `paciente_id` | UUID FK → pacientes | Paciente facturado |
| `obra_social_id` | UUID FK → obras_sociales nullable | OS del paciente (opcional) |
| `numero_comprobante` | str(50) | Número correlativo generado (ej: "REC-000001") |
| `tipo` | str(20) | `factura_a`, `factura_b`, `recibo`, `orden` |
| `fecha_emision` | timestamptz | Fecha de emisión (default: now) |
| `monto_total` | float | Suma de todos los ítems |
| `monto_cobertura` | float | Parte cubierta por la OS |
| `monto_copago` | float | Copago fijo de la OS |
| `monto_particular` | float | Monto a cargo del paciente sin OS |
| `estado` | str(30) | `pendiente`, `pagado`, `cancelado`, `anulado` |
| `concepto` | str(500) | Descripción del servicio |
| `notas` | text nullable | Notas adicionales |
| `pdf_url` | str(500) nullable | URL MinIO del PDF generado |

Constraint único: `(tenant_id, numero_comprobante)`.

### ItemComprobante (`items_comprobante`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador único |
| `comprobante_id` | UUID FK → comprobantes ON DELETE CASCADE | Comprobante padre |
| `descripcion` | str(300) | Descripción del ítem |
| `cantidad` | float | Cantidad (default: 1.0) |
| `precio_unitario` | float | Precio por unidad |
| `subtotal` | float | `cantidad * precio_unitario` (calculado por el servicio) |

---

## API Endpoints

Base path: `/api/v1/facturacion`

| Método | Path | Roles | Descripción |
|---|---|---|---|
| `GET` | `/obras-sociales` | medico, recepcion, admin | Lista obras sociales activas |
| `POST` | `/obras-sociales` | recepcion, admin | Crea una obra social |
| `GET` | `/comprobantes` | medico, recepcion, admin | Lista comprobantes (filtros: `paciente_id`, `estado`, `limit`, `offset`) |
| `POST` | `/comprobantes` | recepcion, admin | Crea un comprobante con sus ítems |
| `GET` | `/comprobantes/{id}` | medico, recepcion, admin | Obtiene comprobante con ítems |
| `PATCH` | `/comprobantes/{id}` | recepcion, admin | Actualiza estado / notas / pdf_url |
| `POST` | `/comprobantes/{id}/pagar` | recepcion, admin | Shortcut: estado → "pagado" |
| `GET` | `/resumen` | recepcion, admin | Resumen del día (o período con `fecha_desde` / `fecha_hasta`) |

---

## Lógica de negocio

### Cálculo de copagos (`FacturacionService.crear_comprobante`)

```
monto_total = sum(item.cantidad * item.precio_unitario for item in items)

Si hay obra_social_id:
    monto_cobertura = monto_total * (obra_social.porcentaje_cobertura / 100)
    monto_copago    = obra_social.copago_consulta   # monto fijo
    monto_particular = 0.0

Sin obra social:
    monto_cobertura  = 0.0
    monto_copago     = 0.0
    monto_particular = monto_total
```

### Numeración correlativa (`FacturacionRepository.get_siguiente_numero`)

Formato: `{PREFIJO}-{N:06d}`

| tipo | prefijo |
|---|---|
| `recibo` | `REC` |
| `factura_a` | `FCTA` |
| `factura_b` | `FCTB` |
| `orden` | `ORD` |

El contador es por `(tenant_id, tipo)`.

---

## Archivos implementados

### Backend

- `backend/models/facturacion.py` — Modelos ORM: ObraSocial, Comprobante, ItemComprobante
- `backend/models/__init__.py` — Exporta los 3 nuevos modelos
- `backend/api/v1/facturacion/__init__.py` — Paquete Python
- `backend/api/v1/facturacion/schemas.py` — Pydantic schemas
- `backend/api/v1/facturacion/repository_facturacion.py` — Capa de acceso a datos
- `backend/api/v1/facturacion/service_facturacion.py` — Lógica de negocio
- `backend/api/v1/facturacion/router.py` — Endpoints FastAPI
- `backend/api/v1/router.py` — Incluye `facturacion_router`
- `backend/alembic/versions/002_facturacion.py` — Migración con RLS y triggers
- `backend/tests/test_facturacion.py` — Suite de tests

### Frontend

- `frontend/app/facturacion/page.tsx` — Página completa con Tabs (Comprobantes / Obras Sociales / Resumen)
- `frontend/components/layout/Sidebar.tsx` — Agrega link a /facturacion con ícono Receipt
- `frontend/lib/api.ts` — Comentario al final con funciones a agregar (no modificado)

---

## Estado de implementación

- [x] Modelos ORM (ObraSocial, Comprobante, ItemComprobante)
- [x] Migración Alembic con RLS y triggers de updated_at
- [x] Schemas Pydantic con validación (Field constraints)
- [x] Repository con filtrado por tenant_id
- [x] Service con lógica de cálculo de copagos
- [x] Router FastAPI con todos los endpoints
- [x] Integración en api/v1/router.py
- [x] Tests pytest-asyncio (6 escenarios)
- [x] Frontend: página con 3 tabs
- [x] Frontend: modales de creación (OS y Comprobante)
- [x] Frontend: botón Pagar en comprobantes pendientes
- [x] Frontend: Sidebar con link a /facturacion
- [ ] Generación de PDF (MinIO) — pendiente MOD_05b
- [ ] Integración turno → comprobante automático — pendiente
- [ ] Exportación a AFIP / fiscal — fuera de scope inicial
