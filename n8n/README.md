# n8n Workflows — OpenClinicIA

## Setup

1. Importar los workflows desde esta carpeta en tu instancia n8n
2. Configurar las credenciales de Telegram Bot
3. Configurar las variables de entorno en n8n:
   - `OPENCLINICA_API_URL=http://api:8000`
   - `N8N_WEBHOOK_SECRET=<mismo valor que en .env del backend>`
   - `INTERNAL_API_TOKEN=<token de servicio del backend>`
   - `TELEGRAM_CLINIC_CHAT_ID=<chat_id del grupo de la clínica>`

## Workflows disponibles

### agente_jefe_telegram.json

Recibe mensajes de Telegram y los procesa con IA (Claude) para ejecutar acciones en OpenClinicIA.

**Comandos soportados:**
- "ver sala de espera" → lista pacientes en sala
- "turnos de hoy" → lista turnos del día
- "buscar paciente [nombre/DNI]" → busca en historia clínica
- "resumen del día" → facturación y turnos completados

### recordatorio_turnos.json

Corre cada hora y envía recordatorios a Telegram para turnos próximos (≤2 horas).

### agente_jefe.json (original)

Webhook genérico sin Telegram para testing.
