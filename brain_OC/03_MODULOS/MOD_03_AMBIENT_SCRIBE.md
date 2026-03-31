# MOD_03 — Ambient Scribe

## Descripción

El módulo Ambient Scribe transforma el audio de una consulta médica en una nota clínica estructurada en formato SOAP (Subjetivo, Objetivo, Assessment, Plan). El pipeline combina OpenAI Whisper para transcripción de voz y Claude Sonnet para generación de la nota clínica.

---

## Arquitectura

```
Audio (URL / Upload)
        │
        ▼
┌───────────────────┐
│  WhisperService   │  ←── OpenAI Whisper API (whisper-1)
│  (async, FastAPI) │       Fallback: transcripción simulada
└────────┬──────────┘
         │  texto transcripto
         ▼
┌────────────────────────┐
│  SOAPGeneratorService  │  ←── Claude Sonnet (claude-sonnet-4-6)
│  (async, Anthropic)    │       Prompt estructurado SOAP
└────────┬───────────────┘
         │  SOAPResponse
         ▼
   Respuesta JSON
```

**Componentes principales:**

| Archivo | Rol |
|---|---|
| `service_whisper.py` | Transcripción async (FastAPI) con fallback |
| `worker_transcripcion.py` | Tareas Celery: transcripción, pipeline completo |
| `service_generacion_soap.py` | Generación de nota SOAP con Claude Sonnet |
| `router.py` | Endpoints FastAPI del módulo |
| `schemas.py` | Modelos Pydantic de request/response |

---

## Flujos

### Flujo 1: Texto directo → SOAP (sync)

```
POST /ia/scribe/generar-soap
  { "transcripcion_texto": "...", "contexto_paciente": "..." }
        │
        ▼
  SOAPGeneratorService.generar_soap()
        │
        ▼
  SOAPResponse (200 OK)
```

Caso de uso: el médico ya tiene el texto transcripto y solo quiere la nota SOAP.

### Flujo 2: Upload directo de audio (sync inmediato)

```
POST /ia/scribe/transcribir   (multipart form)
  audio_file=<bytes>
        │
        ▼
  WhisperService.transcribir_desde_bytes()
        │
        ▼
  TranscripcionResponse { transcripcion, estado: "completado" }
```

Caso de uso: el médico sube el audio directamente desde el browser.

### Flujo 3: URL de audio → pipeline completo (async Celery)

```
POST /ia/scribe/transcribir
  { audio_url: "https://...", episodio_id: "...", contexto: "..." }
        │
        ▼
  transcribir_y_generar_soap.delay()   [Celery task]
        │
        ▼
  TranscripcionResponse { task_id, estado: "procesando" }

  (polling)
  GET /ia/scribe/estado/{task_id}
        │
        ▼
  { estado: "SUCCESS", resultado: { transcripcion, soap, episodio_id } }
```

Caso de uso: audio almacenado en MinIO u otro storage.

---

## Fallback sin API Key

Cuando `OPENAI_API_KEY` está vacía o es un placeholder (`sk-`, `your_openai_api_key_here`):

- `WhisperService` inicia en `modo_fallback=True`
- `_llamar_whisper_sync()` retorna una transcripción médica simulada
- Los workers Celery también usan el mismo fallback
- No se lanza ninguna excepción — el sistema opera normalmente para desarrollo

---

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `OPENAI_API_KEY` | Clave de API de OpenAI para Whisper | `""` (fallback) |
| `WHISPER_MODEL` | Modelo de Whisper a usar | `whisper-1` |
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic para SOAP | `""` |
| `REDIS_URL` | URL de Redis para broker Celery | `redis://localhost:6379/0` |

---

## API Endpoints

### `POST /api/v1/ia/scribe/generar-soap`

Genera nota SOAP a partir de texto transcripto.

**Request:**
```json
{
  "transcripcion_texto": "Paciente refiere dolor lumbar...",
  "contexto_paciente": "Masculino, 45 años, HTA."
}
```

**Response 200:**
```json
{
  "subjetivo": "...",
  "objetivo": "...",
  "assessment": "...",
  "plan": "...",
  "resumen_clinico": "..."
}
```

---

### `POST /api/v1/ia/scribe/transcribir`

Transcribe audio. Acepta `audio_file` (multipart) o `audio_url` (form field).

**Con audio_file (sync):**
```
Content-Type: multipart/form-data
audio_file: <bytes>
episodio_id: "uuid"
```

**Response 202:**
```json
{
  "transcripcion": "Paciente refiere...",
  "estado": "completado"
}
```

**Con audio_url (async Celery):**
```json
{
  "audio_url": "https://storage/audio.mp3",
  "episodio_id": "uuid",
  "contexto": "contexto del paciente"
}
```

**Response 202:**
```json
{
  "task_id": "celery-task-uuid",
  "estado": "procesando"
}
```

---

### `GET /api/v1/ia/scribe/estado/{task_id}`

Consulta estado de tarea Celery.

**Response 200:**
```json
{
  "task_id": "celery-task-uuid",
  "estado": "SUCCESS",
  "resultado": {
    "transcripcion": "...",
    "soap": { "subjetivo": "...", "plan": "..." },
    "episodio_id": "uuid"
  }
}
```

Estados posibles: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`.

---

### `POST /api/v1/ia/scribe/encolar-transcripcion`

Endpoint de compatibilidad para encolar solo la transcripción (sin SOAP).

**Response 202:**
```json
{
  "task_id": "celery-task-uuid",
  "status": "queued",
  "message": "Transcripción encolada correctamente"
}
```

---

## Formatos de audio soportados

| Extensión | MIME type |
|---|---|
| `.mp3` | `audio/mpeg` |
| `.wav` | `audio/wav` |
| `.m4a` | `audio/mp4` |
| `.ogg` | `audio/ogg` |
| `.webm` | `audio/webm` |
| `.flac` | `audio/flac` |

---

## Estado de implementación

- [x] `worker_transcripcion.py` — integración real con Whisper + fallback
- [x] `service_whisper.py` — servicio async para uploads directos
- [x] `router.py` — endpoints `/transcribir`, `/estado/{task_id}`, `/generar-soap`
- [x] `schemas.py` — `TranscripcionRequest`, `TranscripcionResponse`, `PipelineScribeRequest`, `PipelineScribeResponse`
- [x] `core/config.py` — `OPENAI_API_KEY`, `WHISPER_MODEL`
- [x] `requirements.txt` — `openai==1.57.0`
- [x] `.env.example` — variables de Whisper documentadas
- [x] `tests/test_scribe.py` — 4 tests con mocks de Anthropic y Celery
- [ ] Integración con MinIO para persistencia de audio
- [ ] Frontend para upload directo desde consulta
- [ ] Streaming de transcripción en tiempo real
