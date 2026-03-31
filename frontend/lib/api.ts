import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type {
  TokenResponse,
  User,
  Turno,
  SalaEsperaItem,
  Paciente,
  Episodio,
  CreateTurnoData,
  UpdateTurnoData,
  CreateEpisodioData,
  TriajeData,
  TriajeResponse,
  SOAPData,
  SOAPResponse,
  CreatePacienteData,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: string) => void;
  reject: (reason: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else if (token) {
      resolve(token);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken =
          typeof window !== "undefined"
            ? localStorage.getItem("refresh_token")
            : null;

        if (!refreshToken) {
          throw new Error("No refresh token");
        }

        const response = await axios.post<TokenResponse>(
          `${BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token } = response.data;

        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", access_token);
        }

        processQueue(null, access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);

        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export const auth = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await apiClient.post<TokenResponse>("/auth/token", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return response.data;
  },

  refreshToken: async (token: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>("/auth/refresh", {
      refresh_token: token,
    });
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>("/auth/me");
    return response.data;
  },
};

export const agenda = {
  getTurnos: async (fecha: string, medico_id?: string): Promise<Turno[]> => {
    const params: Record<string, string> = { fecha };
    if (medico_id) {
      params.medico_id = medico_id;
    }
    const response = await apiClient.get<Turno[]>("/turnos", { params });
    return response.data;
  },

  createTurno: async (data: CreateTurnoData): Promise<Turno> => {
    const response = await apiClient.post<Turno>("/turnos", data);
    return response.data;
  },

  updateTurno: async (id: string, data: UpdateTurnoData): Promise<Turno> => {
    const response = await apiClient.patch<Turno>(`/turnos/${id}`, data);
    return response.data;
  },

  getSalaEspera: async (): Promise<SalaEsperaItem[]> => {
    const response = await apiClient.get<SalaEsperaItem[]>("/sala-espera");
    return response.data;
  },

  ingresarSala: async (id: string): Promise<Turno> => {
    const response = await apiClient.post<Turno>(`/turnos/${id}/ingresar-sala`);
    return response.data;
  },
};

export const pacientes = {
  searchPacientes: async (q: string): Promise<Paciente[]> => {
    const response = await apiClient.get<Paciente[]>("/pacientes", {
      params: { q },
    });
    return response.data;
  },

  getPaciente: async (id: string): Promise<Paciente> => {
    const response = await apiClient.get<Paciente>(`/pacientes/${id}`);
    return response.data;
  },

  createPaciente: async (data: CreatePacienteData): Promise<Paciente> => {
    const response = await apiClient.post<Paciente>("/pacientes", data);
    return response.data;
  },

  getHistoria: async (paciente_id: string): Promise<Episodio[]> => {
    const response = await apiClient.get<Episodio[]>(
      `/pacientes/${paciente_id}/historia`
    );
    return response.data;
  },

  createEpisodio: async (
    paciente_id: string,
    data: CreateEpisodioData
  ): Promise<Episodio> => {
    const response = await apiClient.post<Episodio>(
      `/pacientes/${paciente_id}/episodios`,
      data
    );
    return response.data;
  },
};

export const ia = {
  evaluarTriaje: async (data: TriajeData): Promise<TriajeResponse> => {
    const response = await apiClient.post<TriajeResponse>("/ia/triaje", data);
    return response.data;
  },

  generarSOAP: async (data: SOAPData): Promise<SOAPResponse> => {
    const response = await apiClient.post<SOAPResponse>("/ia/soap", data);
    return response.data;
  },
};

export default apiClient;

// ─── MOD_05 Facturación — funciones a agregar ────────────────────────────────
//
// Las siguientes funciones deberían agregarse a este archivo para soportar
// el módulo de Facturación. No se agregan aquí para respetar la regla
// "NO MODIFICAR" — se implementaron directamente en la página de facturación.
//
// export const facturacion = {
//   getObrasSociales: async (): Promise<ObraSocial[]>
//     → GET /api/v1/facturacion/obras-sociales
//
//   createObraSocial: async (data: ObraSocialCreate): Promise<ObraSocial>
//     → POST /api/v1/facturacion/obras-sociales
//
//   getComprobantes: async (params?: {
//     paciente_id?: string;
//     estado?: string;
//     limit?: number;
//     offset?: number;
//   }): Promise<Comprobante[]>
//     → GET /api/v1/facturacion/comprobantes
//
//   getComprobante: async (id: string): Promise<Comprobante>
//     → GET /api/v1/facturacion/comprobantes/{id}
//
//   createComprobante: async (data: ComprobanteCreate): Promise<Comprobante>
//     → POST /api/v1/facturacion/comprobantes
//
//   updateComprobante: async (
//     id: string,
//     data: { estado?: string; notas?: string; pdf_url?: string }
//   ): Promise<Comprobante>
//     → PATCH /api/v1/facturacion/comprobantes/{id}
//
//   pagarComprobante: async (id: string): Promise<Comprobante>
//     → POST /api/v1/facturacion/comprobantes/{id}/pagar
//
//   getResumen: async (params?: {
//     fecha_desde?: string;
//     fecha_hasta?: string;
//   }): Promise<ResumenFacturacion>
//     → GET /api/v1/facturacion/resumen
// };
