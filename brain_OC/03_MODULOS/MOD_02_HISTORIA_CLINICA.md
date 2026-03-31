# MOD_02 — Historia Clínica (EHR)

> **Estado:** 🟡 En progreso
> **Módulo:** Historia Clínica Electrónica
> **Dependencias:** MOD_01 Agenda, Auth

---

## Descripción

Sistema de Historia Clínica Electrónica (EHR) que permite registrar, consultar y gestionar los episodios clínicos de cada paciente. Integrado con el Ambient Scribe (MOD_03) para generar notas SOAP automáticamente desde transcripciones de consultas.

---

## Modelo de Datos

### Tabla: episodios

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID | PK |
| tenant_id | UUID | FK tenants (RLS) |
| paciente_id | UUID | FK pacientes |
| turno_id | UUID | FK turnos (nullable) |
| medico_id | UUID | FK usuarios |
| fecha | timestamptz | Fecha/hora del episodio |
| motivo_consulta | text | Motivo principal (requerido) |
| anamnesis | text | Historia de la enfermedad actual |
| examen_fisico | text | Hallazgos del examen físico |
| diagnostico | text | Diagnóstico(s) en CIE-10 (futuro) |
| plan_terapeutico | text | Plan de tratamiento |
| soap_subjetivo | text | SOAP: S — síntomas referidos |
| soap_objetivo | text | SOAP: O — hallazgos objetivos |
| soap_assessment | text | SOAP: A — diagnóstico/impresión |
| soap_plan | text | SOAP: P — plan de acción |
| transcripcion_raw | text | Texto crudo de la transcripción |
| created_at | timestamptz | Creación |
| updated_at | timestamptz | Última modificación |

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/v1/pacientes/{id}/historia | Listar episodios del paciente |
| POST | /api/v1/pacientes/{id}/episodios | Crear nuevo episodio |
| GET | /api/v1/pacientes/{id}/episodios/{eid} | Obtener episodio |
| PATCH | /api/v1/pacientes/{id}/episodios/{eid} | Actualizar episodio |
| POST | /api/v1/ia/scribe/generar-soap | Generar SOAP desde transcripción |

---

## Flujo Principal

```
1. Turno → en_atencion
   ↓
2. Médico crea episodio (motivo_consulta)
   ↓
3. [Opcional] Grabación → Whisper → transcripcion_raw
   ↓
4. [Opcional] transcripcion_raw → Claude Sonnet → notas SOAP
   ↓
5. Médico revisa/edita y confirma
   ↓
6. Episodio guardado → Turno → completado
```

---

## Seguridad y Privacidad

- **RLS activo:** cada episodio solo visible para su tenant
- **Logs:** se usa `[PACIENTE_{id}]` y `[EPISODIO_{id}]` como tokens, nunca nombre real
- **Encriptación en reposo:** planificada para campos sensibles (fase 2)
- **Auditoría:** toda modificación registra medico_id + timestamp

---

## Integración con IA (MOD_03 Ambient Scribe)

El módulo EHR consume el servicio `SOAPGeneratorService` del Ambient Scribe:

```python
soap = await soap_generator.generar_soap(
    transcripcion=episodio.transcripcion_raw,
    contexto=f"Paciente {episodio.paciente_id}, motivo: {episodio.motivo_consulta}"
)
```

El resultado se mapea directamente a los campos `soap_*` del episodio.

---

## Estado de Implementación

- [x] Modelo SQLAlchemy `Episodio`
- [x] Migración Alembic 001
- [x] Repository `EpisodioRepository`
- [x] Service `HistoriaClinicaService`
- [x] Router con endpoints CRUD
- [x] Schemas Pydantic
- [x] Tests básicos
- [ ] Búsqueda full-text con pg_trgm
- [ ] Codificación CIE-10 automática
- [ ] Adjuntos (PDF, imágenes) vía MinIO
- [ ] Vista de línea de tiempo en frontend

---

*Última actualización: 2026-03-30*
