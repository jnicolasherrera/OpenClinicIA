# 🏥 OpenClinicIA — Tablero Principal

> **Vault:** `brain_OC` · **Versión:** 0.1.0 · **Estado:** 🟡 En construcción  
> **Repositorio:** [github.com/jnicolasherrera/OpenClinicIA](https://github.com/jnicolasherrera/OpenClinicIA)  
> **Licencia:** MIT Open Source

---

## ¿Qué es OpenClinicIA?

Plataforma integral **open-source** para la gestión clínica con Inteligencia Artificial integrada. Diseñada para clínicas, consultorios y centros de salud que quieren automatizar tareas de alto valor sin depender de software propietario caro.

**Stack central:** FastAPI · Next.js · PostgreSQL · Redis · MinIO · n8n · Claude API · Whisper · Docker

---

## 🗺️ Mapa del Vault

### Arquitectura & Estándares
- [[01_ARQUITECTURA_MAESTRA]] — Fuente de verdad del sistema completo
- [[02_ESTANDARES_CODING]] — Ley de escritura de código para humanos e IA
- [[05_STACK_TECNOLOGICO]] — Decisiones de tecnología justificadas
- [[07_ADR/ADR_001_fastapi_vs_django]] — Por qué FastAPI
- [[07_ADR/ADR_002_pgvector_vs_pinecone]] — Por qué pgvector en MVP

### Módulos del Sistema
- [[03_MODULOS/MOD_01_AGENDA]] — Turnos y calendario multiprofesional
- [[03_MODULOS/MOD_02_HISTORIA_CLINICA]] — EHR y portal del paciente
- [[03_MODULOS/MOD_03_AMBIENT_SCRIBE]] — Transcripción consulta → SOAP
- [[03_MODULOS/MOD_04_TRIAJE_IA]] — Clasificación de urgencia pre-turno
- [[03_MODULOS/MOD_05_FACTURACION]] — Coberturas, copagos y comprobantes
- [[03_MODULOS/MOD_06_ARBOL_AGENTES]] — n8n Jefe→Gerente→Trabajador
- [[03_MODULOS/MOD_07_LABORATORIO]] — Muestras, LIS/PACS, stock
- [[03_MODULOS/MOD_08_TELEMEDICINA]] — Videoconsulta WebRTC y wearables

### IA & Aprendizaje
- [[04_APRENDIZAJE_CONTINUO_IA]] — RAG enriquecido y Data Flywheel clínico

### Gestión del Proyecto
- [[06_ROADMAP]] — 5 fases desde MVP hasta SaaS
- [[08_COSTOS_OPEX]] — Análisis financiero mensual
- [[09_PRIVACIDAD_LEGAL]] — Cumplimiento HIPAA · GDPR · Ley 25.326 · Ley 1581
- [[10_CONTRIBUIR]] — Guía para contribuidores open-source
- [[11_ESTADO_DIARIO]] — Log de progreso diario

---

## 📊 Estado del Proyecto

| Módulo | Estado | Notas |
|--------|--------|-------|
| Vault brain_OC | 🟢 Activo | Este documento |
| Repo GitHub público | 🟢 Creado | MIT · jnicolasherrera/OpenClinicIA |
| Docker Compose base | 🟢 Creado | Stack completo local |
| CI/CD GitHub Actions | 🟢 Creado | lint + test en cada PR |
| MOD_01 Agenda | 🔲 Pendiente | Primer módulo a desarrollar |
| MOD_02 EHR | 🔲 Pendiente | |
| MOD_03 Ambient Scribe | 🔲 Pendiente | |
| MOD_04 Triaje IA | 🔲 Pendiente | |
| MOD_05 Facturación | 🔲 Pendiente | |
| MOD_06 Árbol Agentes n8n | 🔲 Pendiente | |
| Backend FastAPI base | 🔲 Pendiente | Próxima sesión |
| Frontend Next.js base | 🔲 Pendiente | |

---

## 🤖 Instrucciones para el Agente IA

> Este vault es la **memoria persistente** de OpenClinicIA. Cada vez que trabajes en este proyecto, tu primera acción es leer este tablero y los documentos referenciados relevantes.

### Reglas del agente
1. **Nunca inventés arquitectura** sin actualizar el vault primero.
2. **Cada módulo nuevo** requiere su nota en `03_MODULOS/`.
3. **Cada decisión técnica mayor** requiere un ADR en `07_ADR/`.
4. **El `11_ESTADO_DIARIO`** se actualiza al final de cada sesión de trabajo.
5. **Nunca subas secrets** al repo. Todo en `.env.example`.
6. **Los commits siguen** el estándar de [[02_ESTANDARES_CODING]].

---

## 🔗 Links Rápidos

- [Repo GitHub](https://github.com/jnicolasherrera/OpenClinicIA)
- [Issues](https://github.com/jnicolasherrera/OpenClinicIA/issues)
- [Projects / Kanban](https://github.com/jnicolasherrera/OpenClinicIA/projects)

---

*Última actualización: 2026-03-31*
