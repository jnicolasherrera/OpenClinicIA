# Estándares de Codificación — [NOMBRE_PROYECTO]

<- Volver al [[00_TABLERO_PRINCIPAL|Tablero Principal]]

Este documento define la ley inquebrantable sobre cómo los desarrolladores (humanos e IA) deben escribir, nombrar y documentar el código fuente del ecosistema **[NOMBRE_PROYECTO]**.

---

## 1. Nomenclatura Significativa (Clean Code)

**Regla de oro:** El nombre del archivo debe describir exactamente su única responsabilidad.

### ❌ Prohibido
```
script.py     utils.js     helpers.py     data.ts     misc.go
manager.py    common.ts    stuff.js       temp.py
```

### ✅ Correcto
```
ingestor_webhook_outlook.py        → Ingesta de webhooks de Outlook
middleware_rls_auth.ts             → Middleware de autenticación con RLS
consumer_ia_clasificacion.py       → Consumidor Kafka que clasifica con IA
service_notificacion_email.ts      → Servicio de envío de emails
repository_casos_pqr.py            → Repositorio de acceso a datos de casos
```

**Patrón recomendado:** `[capa]_[dominio]_[accion].[ext]`

---

## 2. Documentación Exhaustiva (Trazabilidad 1:1)

Cada archivo de código **debe tener su nota gemela** en esta bóveda.

Un módulo **no se considera "Terminado"** hasta que no aparezca su documentación funcional en `Brain/` con:

- [ ] Descripción de la responsabilidad única del módulo
- [ ] Parámetros de entrada y tipos esperados
- [ ] Estructura de la respuesta / salida
- [ ] Manejo de errores y casos borde
- [ ] Dependencias externas y cómo se inyectan
- [ ] Ejemplo de uso / llamada de prueba

Esto garantiza que cualquier futuro arquitecto entienda el **POR QUÉ** detrás del código sin leerlo línea por línea.

---

## 3. Código Hiper-Comentado

### Docstrings (Python)
```python
def clasificar_pqr(texto: str, tenant_id: UUID) -> ClasificacionResult:
    """
    Clasifica el tipo y prioridad de una PQR usando el motor de IA.

    Se llama desde el Worker de Kafka después de validar el evento.
    NO debe llamarse directamente desde el API para evitar latencia síncrona.

    Args:
        texto: Cuerpo del mensaje ya limpiado (sin HTML, sin adjuntos).
        tenant_id: UUID del tenant para inyectar contexto de su industria.

    Returns:
        ClasificacionResult con tipo, prioridad, resumen y fecha_vencimiento.

    Raises:
        AIRateLimitError: Si la IA devuelve 429. El caller debe aplicar backoff.
        TenantNotFoundError: Si el tenant_id no existe en la base de datos.
    """
```

### JSDoc (TypeScript)
```typescript
/**
 * Suscribe al canal SSE del tenant autenticado para recibir eventos en tiempo real.
 *
 * Requiere que el JWT en el header Authorization sea válido y corresponda
 * al mismo tenant_id del canal. Rechaza conexiones cross-tenant.
 *
 * @param tenantId - UUID del tenant extraído del JWT decodificado
 * @returns EventSource conectado al canal privado del tenant
 * @throws AuthError si el JWT está expirado o el tenant no coincide
 */
```

---

## 4. Estándares por Lenguaje

| Lenguaje | Linter / Formatter | Type Checker | Test Runner | Cobertura Mínima |
|---|---|---|---|---|
| Python | `ruff` + `black` | `mypy --strict` | `pytest` | [80%] |
| TypeScript | `ESLint` + `Prettier` | `tsc --strict` | `Jest` / `Vitest` | [75%] |
| Go | `gofmt` + `staticcheck` | Built-in | `go test` | [80%] |
| [Otro] | [Herramienta] | [Herramienta] | [Herramienta] | [X%] |

### Reglas globales
- **Cero `Any`:** No se aceptan tipos `any` en TypeScript ni `Any` en mypy. Si no se puede tipar, abrir un issue.
- **Sin secrets en código:** Toda credencial va en variables de entorno. El CI/CD tiene un scanner de secrets.
- **Sin dead code:** No quedan `print()`, `console.log()`, ni bloques comentados de código viejo.

---

## 5. Trazabilidad de Commits (Semantic Versioning)

### Estructura del mensaje
```
tipo(alcance): descripción breve en imperativo y minúsculas

[Cuerpo opcional: el POR QUÉ del cambio, no el QUÉ]
```

### Tipos permitidos

| Prefijo | Cuándo usarlo | Ejemplo |
|---|---|---|
| `feat:` | Nueva funcionalidad | `feat(api): implementar rls para tenants` |
| `fix:` | Corrección de bug | `fix(ia): corregir timeout en clasificacion` |
| `docs:` | Solo documentación | `docs: actualizar flujo de kafka en modulo 01` |
| `refactor:` | Mejora sin cambio de comportamiento | `refactor(db): simplificar query de auditoria` |
| `perf:` | Mejora de rendimiento | `perf(db): agregar indice gin para busqueda` |
| `test:` | Añadir o corregir tests | `test(ingestor): mock de webhook graph api` |
| `chore:` | Mantenimiento / dependencias | `chore: actualizar fastapi a 0.115` |
| `style:` | Formato puro (sin lógica) | `style: aplicar ruff format al modulo backend` |

### Reglas de oro
1. **Commits atómicos:** Un commit = un solo cambio lógico. No mezclar CSS con lógica de BD.
2. **Imperativo:** `feat: crear tabla` — NO `creando tabla` ni `se crea tabla`.
3. **Frecuencia:** 10 commits pequeños > 1 commit gigante de "fin del día".
4. **Main siempre verde:** La rama principal siempre debe estar en estado deployable.

---

## 6. Definition of Done (DoD)

Un ticket **solo se cierra** cuando cumple TODOS los puntos:

- [ ] **Lógica implementada:** El código cumple el criterio de aceptación.
- [ ] **Documentación Brain:** El archivo `.md` gemelo en esta bóveda está actualizado.
- [ ] **Tests verificados:** La cobertura no decreció respecto al baseline anterior.
- [ ] **Lint & Types:** Pasa `ruff`/`ESLint` y el type checker sin errores ni warnings.
- [ ] **Clean Code:** Sin `print()`, `console.log()`, ni comentarios de código muerto.
- [ ] **Correlation ID:** Presente en todos los logs del nuevo flujo de datos.
- [ ] **Security check:** Sin fugas de `tenant_id` ni credenciales en queries o logs.
