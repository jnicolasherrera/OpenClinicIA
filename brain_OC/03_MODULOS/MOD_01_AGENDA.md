# MOD_01 — Agenda y Turnos

> **Estado:** 🟡 En progreso
> **Módulo:** Sistema de turnos y gestión de sala de espera
> **Dependencias:** Auth

---

## Descripción

Sistema de gestión de turnos médicos con soporte multi-profesional, multi-tenant y sala de espera en tiempo real. Permite programar, confirmar, cancelar y gestionar el flujo de atención desde la recepción.

---

## Estados de un Turno

```
programado → confirmado → en_sala → en_atencion → completado
                ↓                        ↓
             cancelado               ausente
```

---

## Modelo de Datos

### Tabla: turnos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID | PK |
| tenant_id | UUID | FK tenants (RLS) |
| paciente_id | UUID | FK pacientes |
| medico_id | UUID | FK usuarios |
| fecha_hora | timestamptz | Inicio del turno |
| duracion_minutos | int | Duración (default 30) |
| estado | varchar(50) | Estado actual (ver FSM arriba) |
| motivo | varchar(500) | Motivo de consulta |
| notas | text | Notas internas |
| sala_espera_ingreso | timestamptz | Cuando llegó el paciente |
| created_at | timestamptz | Creación |
| updated_at | timestamptz | Última modificación |

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/v1/agenda/turnos | Listar turnos (filtro fecha/médico) |
| POST | /api/v1/agenda/turnos | Crear turno |
| PATCH | /api/v1/agenda/turnos/{id} | Actualizar turno |
| DELETE | /api/v1/agenda/turnos/{id} | Cancelar turno |
| GET | /api/v1/agenda/sala-espera | Ver sala de espera actual |
| POST | /api/v1/agenda/turnos/{id}/ingresar-sala | Registrar llegada del paciente |

---

## Lógica de Negocio

- **Anti-solapamiento:** Al crear turno, valida que el médico no tenga otro turno en el mismo slot (± duración)
- **Sala de espera:** Filtra turnos con estado `en_sala` ordenados por `sala_espera_ingreso`
- **Tiempo de espera:** Calculado como `now() - sala_espera_ingreso`

---

## Estado de Implementación

- [x] Modelo SQLAlchemy `Turno`
- [x] Migración Alembic 001
- [x] Repository `TurnoRepository`
- [x] Service `AgendaService` con validación anti-solapamiento
- [x] Router con endpoints completos
- [x] Schemas Pydantic
- [x] Tests básicos
- [ ] Recordatorios automáticos (SMS/email) vía n8n
- [ ] Reserva online por paciente
- [ ] Vista semanal/mensual en frontend (parcial)

---

*Última actualización: 2026-03-30*
