# 🏥 OpenClinicIA

**Plataforma open-source para gestión clínica con Inteligencia Artificial integrada**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## ¿Qué es OpenClinicIA?

Plataforma integral open-source para clínicas, consultorios y centros de salud que combina gestión administrativa con un núcleo de IA que aprende del equipo médico.

**Stack:** FastAPI · Next.js · PostgreSQL + pgvector · Redis · MinIO · n8n · Claude API · Whisper · Docker

## Funcionalidades

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| 📅 Agenda inteligente | Turnos, sala de espera virtual | 🔲 En desarrollo |
| 🏥 Historia Clínica EHR | Registro longitudinal, portal paciente | 🔲 En desarrollo |
| 🎙️ Ambient Scribe | Consulta → nota SOAP con IA | 🔲 En desarrollo |
| 🤖 Triaje IA | Clasifica urgencia antes del turno | 🔲 En desarrollo |
| 💰 Facturación | Obras sociales, copagos | 🔲 En desarrollo |
| 🧠 Árbol de Agentes | Automatización admin vía n8n | 🔲 Planificado |
| 💻 Telemedicina | Videoconsulta + wearables | 🔲 Planificado |

## Inicio Rápido
```bash
git clone https://github.com/jnicolasherrera/OpenClinicIA.git
cd OpenClinicIA
cp .env.example .env
# Editá .env con tus API keys
bash scripts/setup.sh
```

## Documentación

El directorio `brain_OC/` es un vault Obsidian con la documentación completa.
Abrilo con [Obsidian](https://obsidian.md/) y empezá por `00_TABLERO_PRINCIPAL.md`.

## Licencia

MIT — libre para usar, modificar y distribuir.

---
*Hecho para democratizar tecnología clínica de calidad en LATAM y el mundo.*
