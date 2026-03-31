export interface User {
  id: string;
  email: string;
  nombre: string;
  apellido: string;
  rol: "medico" | "recepcion" | "admin" | "paciente";
}

export interface Paciente {
  id: string;
  numero_historia: string;
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  dni: string;
  telefono: string;
  email?: string;
  obra_social?: string;
}

export interface Turno {
  id: string;
  paciente_id: string;
  medico_id: string;
  fecha_hora: string;
  duracion_minutos: number;
  estado:
    | "programado"
    | "confirmado"
    | "en_sala"
    | "en_atencion"
    | "completado"
    | "cancelado"
    | "ausente";
  motivo?: string;
  notas?: string;
  paciente_nombre?: string;
  medico_nombre?: string;
}

export interface SalaEsperaItem {
  turno_id: string;
  paciente_nombre: string;
  medico_nombre: string;
  hora_turno: string;
  estado: string;
  tiempo_espera_minutos: number;
}

export interface Episodio {
  id: string;
  fecha: string;
  motivo_consulta: string;
  diagnostico?: string;
  soap_subjetivo?: string;
  soap_objetivo?: string;
  soap_assessment?: string;
  soap_plan?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CreateTurnoData {
  paciente_id: string;
  medico_id: string;
  fecha_hora: string;
  duracion_minutos: number;
  motivo?: string;
  notas?: string;
}

export interface UpdateTurnoData {
  estado?: Turno["estado"];
  motivo?: string;
  notas?: string;
  fecha_hora?: string;
  duracion_minutos?: number;
}

export interface CreateEpisodioData {
  motivo_consulta: string;
  diagnostico?: string;
  soap_subjetivo?: string;
  soap_objetivo?: string;
  soap_assessment?: string;
  soap_plan?: string;
}

export interface TriajeData {
  paciente_id: string;
  sintomas: string;
  edad?: number;
  antecedentes?: string;
}

export interface TriajeResponse {
  nivel_urgencia: "bajo" | "medio" | "alto" | "critico";
  recomendacion: string;
  tiempo_espera_sugerido: number;
}

export interface SOAPData {
  paciente_id: string;
  episodio_id: string;
  notas_medico: string;
}

export interface SOAPResponse {
  subjetivo: string;
  objetivo: string;
  assessment: string;
  plan: string;
}

export interface CreatePacienteData {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  dni: string;
  telefono: string;
  email?: string;
  obra_social?: string;
}
