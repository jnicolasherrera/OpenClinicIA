# MOD_06 — Árbol de Agentes n8n + Telegram

## Descripción

Módulo de automatización inteligente que conecta Telegram con OpenClinicIA mediante un árbol jerárquico de agentes de IA. Los médicos y recepcionistas envían mensajes en lenguaje natural al bot de Telegram y el sistema interpreta la intención, ejecuta la acción correspondiente y responde automáticamente.

## Diagrama de Flujo

```
Usuario Telegram
      │
      ▼
[n8n — Telegram Trigger]
      │
      ▼
[n8n — HTTP POST /api/v1/agentes/webhook/telegram]
      │   Header: X-N8N-Secret
      ▼
┌─────────────────────────────────────────────┐
│             AGENTE JEFE                     │
│         (Claude Sonnet 4.6)                 │
│  Clasifica intención → JSON estructurado    │
└─────────────┬───────────────────────────────┘
              │ DecisionJefe
              │
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
┌───────┐  ┌────────┐  ┌──────────────┐
│GERENTE│  │GERENTE │  │   GERENTE    │
│AGENDA │  │HISTORIA│  │NOTIFICACIONES│
│       │  │CLINICA │  │              │
└───┬───┘  └───┬────┘  └──────┬───────┘
    │          │               │
    ▼          ▼               ▼
API REST   API REST      Telegram Bot API
/agenda    /pacientes    sendMessage
/turnos    /historia
```

## Componentes

### AgenteJefe (`agent_jefe.py`)

Recibe el texto del mensaje y llama a Claude Sonnet 4.6 con temperatura 0 para obtener una decisión de ruteo en formato JSON estructurado. Maneja errores de parseo devolviendo respuestas amigables al usuario.

- Modelo: `claude-sonnet-4-6`
- Temperatura: 0 (respuestas deterministas)
- Retorna: `DecisionJefe` con tipo_agente, accion, parametros, razonamiento

### GerenteAgenda (`agent_gerente_agenda.py`)

Ejecuta operaciones de turnos llamando a la API REST interna del backend.

| Acción | Descripción |
|--------|-------------|
| `sala_espera` | Lista pacientes en sala con nombres y horarios |
| `ver_turnos` | Turnos del día formateados con estados |
| `crear_turno` | Crea turno si hay datos suficientes, si no los solicita |
| `cancelar_turno` | Cancela turno por ID |

### GerenteNotificaciones (`agent_gerente_notificaciones.py`)

Envía mensajes directamente via Telegram Bot API.

- Método: `sendMessage` con `parse_mode: Markdown`
- Logging sin PII (solo token de chat enmascarado)

## API Endpoints

### `POST /api/v1/agentes/webhook/telegram`

Webhook principal, invocado por n8n al recibir un mensaje de Telegram.

**Autenticación:** Header `X-N8N-Secret` (no requiere JWT)

**Body:**
```json
{
  "chat_id": 123456789,
  "message_id": 42,
  "texto": "ver sala de espera",
  "usuario_telegram": "dr_garcia",
  "fecha": "1711800000"
}
```

**Response:**
```json
{
  "exito": true,
  "mensaje": "🏥 *Sala de Espera*\n\n1. *Juan Pérez*\n   🕐 10:30\n   👨‍⚕️ Dr. García",
  "datos": {"cantidad": 1},
  "error": null
}
```

### `GET /api/v1/agentes/estado`

Health check del sistema de agentes. Requiere JWT.

**Response:**
```json
{
  "agentes_activos": ["jefe", "agenda", "notificaciones"],
  "n8n_configurado": true,
  "telegram_configurado": true,
  "anthropic_configurado": true
}
```

## Variables de Entorno Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | `1234567890:AAExxxxx` |
| `N8N_WEBHOOK_SECRET` | Secret compartido entre n8n y el backend | `s3cr3t-r4nd0m-str1ng` |
| `N8N_BASE_URL` | URL interna de n8n | `http://n8n:5678` |
| `INTERNAL_API_TOKEN` | Token de servicio para llamadas internas | `tok3n-d3-s3rv1c10` |
| `ANTHROPIC_API_KEY` | API key de Anthropic (ya existente en MOD_04/05) | `sk-ant-...` |

## Setup del Telegram Bot

1. Hablar con [@BotFather](https://t.me/BotFather) en Telegram
2. Ejecutar `/newbot` y seguir las instrucciones
3. Copiar el token generado a `TELEGRAM_BOT_TOKEN` en el `.env`
4. Agregar el bot al grupo o chat de la clínica
5. Obtener el `chat_id` del grupo (usar `/getUpdates` en la Bot API)
6. Configurar `TELEGRAM_CLINIC_CHAT_ID` en n8n

## Setup de Workflows n8n

1. Abrir n8n en `http://localhost:5678`
2. Ir a **Settings → Credentials** y crear credencial `Telegram Bot` con el token
3. Ir a **Workflows → Import** y cargar los archivos JSON de `/n8n/workflows/`
4. Configurar las variables de entorno en n8n (Settings → Environment Variables)
5. Activar los workflows

## Estado de Implementación

| Componente | Estado |
|------------|--------|
| `AgenteJefe` — clasificación de intenciones | Implementado |
| `GerenteAgenda` — sala de espera | Implementado |
| `GerenteAgenda` — ver/crear/cancelar turnos | Implementado |
| `GerenteNotificaciones` — envío Telegram | Implementado |
| `GerenteHistoria` — búsqueda pacientes | Pendiente MOD_07 |
| `GerenteFacturacion` — resumen del día | Pendiente MOD_07 |
| Workflow `agente_jefe_telegram.json` | Implementado |
| Workflow `recordatorio_turnos.json` | Implementado |
| Tests unitarios agentes | Pendiente |
