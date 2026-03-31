"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Receipt, Building2, BarChart3, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import apiClient from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ObraSocial {
  id: string;
  nombre: string;
  codigo: string;
  plan?: string;
  porcentaje_cobertura: number;
  copago_consulta: number;
  activa: boolean;
  notas?: string;
}

interface ItemComprobante {
  id: string;
  descripcion: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface Comprobante {
  id: string;
  paciente_id: string;
  obra_social_id?: string;
  numero_comprobante: string;
  tipo: string;
  fecha_emision: string;
  monto_total: number;
  monto_cobertura: number;
  monto_copago: number;
  monto_particular: number;
  estado: string;
  concepto: string;
  notas?: string;
  pdf_url?: string;
  items: ItemComprobante[];
}

interface ResumenFacturacion {
  total_comprobantes: number;
  monto_total: number;
  monto_cobrado: number;
  monto_pendiente: number;
  por_obra_social: { nombre: string; cantidad: number; monto: number }[];
}

// ─── Schemas de validación ────────────────────────────────────────────────────

const obraSocialSchema = z.object({
  nombre: z.string().min(1, "El nombre es requerido"),
  codigo: z.string().min(1, "El código es requerido"),
  plan: z.string().optional(),
  porcentaje_cobertura: z.coerce.number().min(0).max(100),
  copago_consulta: z.coerce.number().min(0),
  notas: z.string().optional(),
});

const itemSchema = z.object({
  descripcion: z.string().min(1, "La descripción es requerida"),
  cantidad: z.coerce.number().min(0.01, "Cantidad debe ser mayor a 0"),
  precio_unitario: z.coerce.number().min(0, "El precio debe ser >= 0"),
});

const comprobanteSchema = z.object({
  paciente_id: z.string().uuid("UUID de paciente inválido"),
  obra_social_id: z.string().uuid().optional().or(z.literal("")),
  tipo: z.enum(["factura_a", "factura_b", "recibo", "orden"]),
  concepto: z.string().min(1, "El concepto es requerido"),
  notas: z.string().optional(),
  items: z.array(itemSchema).min(1, "Al menos un ítem es requerido"),
});

type ObraSocialForm = z.infer<typeof obraSocialSchema>;
type ComprobanteForm = z.infer<typeof comprobanteSchema>;

// ─── API functions ────────────────────────────────────────────────────────────

const BASE = "/api/v1/facturacion";

async function fetchObras(): Promise<ObraSocial[]> {
  const res = await apiClient.get<ObraSocial[]>(`${BASE}/obras-sociales`);
  return res.data;
}

async function createObra(data: ObraSocialForm): Promise<ObraSocial> {
  const res = await apiClient.post<ObraSocial>(`${BASE}/obras-sociales`, data);
  return res.data;
}

async function fetchComprobantes(params?: {
  estado?: string;
}): Promise<Comprobante[]> {
  const res = await apiClient.get<Comprobante[]>(`${BASE}/comprobantes`, {
    params,
  });
  return res.data;
}

async function createComprobante(
  data: ComprobanteForm
): Promise<Comprobante> {
  const payload = {
    ...data,
    obra_social_id: data.obra_social_id || undefined,
  };
  const res = await apiClient.post<Comprobante>(
    `${BASE}/comprobantes`,
    payload
  );
  return res.data;
}

async function pagarComprobante(id: string): Promise<Comprobante> {
  const res = await apiClient.post<Comprobante>(
    `${BASE}/comprobantes/${id}/pagar`
  );
  return res.data;
}

async function fetchResumen(): Promise<ResumenFacturacion> {
  const res = await apiClient.get<ResumenFacturacion>(`${BASE}/resumen`);
  return res.data;
}

// ─── Helpers de presentación ─────────────────────────────────────────────────

const estadoBadge: Record<string, string> = {
  pendiente: "bg-yellow-100 text-yellow-800",
  pagado: "bg-green-100 text-green-800",
  cancelado: "bg-gray-100 text-gray-600",
  anulado: "bg-red-100 text-red-700",
};

const tipoLabel: Record<string, string> = {
  factura_a: "Factura A",
  factura_b: "Factura B",
  recibo: "Recibo",
  orden: "Orden",
};

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(value);
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = "comprobantes" | "obras_sociales" | "resumen";

// ─── Componente principal ─────────────────────────────────────────────────────

export default function FacturacionPage() {
  const [activeTab, setActiveTab] = useState<Tab>("comprobantes");
  const [filtroEstado, setFiltroEstado] = useState<string>("todos");
  const [showNuevoComprobante, setShowNuevoComprobante] = useState(false);
  const [showNuevaOS, setShowNuevaOS] = useState(false);
  const [itemCount, setItemCount] = useState(1);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // ─── Queries ────────────────────────────────────────────────────────────────

  const { data: obras = [] } = useQuery({
    queryKey: ["obras-sociales"],
    queryFn: fetchObras,
  });

  const { data: comprobantes = [], isLoading: loadingComprobantes } = useQuery(
    {
      queryKey: ["comprobantes", filtroEstado],
      queryFn: () =>
        fetchComprobantes(
          filtroEstado !== "todos" ? { estado: filtroEstado } : undefined
        ),
    }
  );

  const { data: resumen } = useQuery({
    queryKey: ["facturacion-resumen"],
    queryFn: fetchResumen,
    enabled: activeTab === "resumen",
  });

  // ─── Mutations ──────────────────────────────────────────────────────────────

  const mutCreateOS = useMutation({
    mutationFn: createObra,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["obras-sociales"] });
      setShowNuevaOS(false);
      osForm.reset();
      toast({ title: "Obra social creada exitosamente" });
    },
    onError: () => {
      toast({ title: "Error al crear la obra social", variant: "destructive" });
    },
  });

  const mutCreateComprobante = useMutation({
    mutationFn: createComprobante,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comprobantes"] });
      queryClient.invalidateQueries({ queryKey: ["facturacion-resumen"] });
      setShowNuevoComprobante(false);
      compForm.reset();
      setItemCount(1);
      toast({ title: "Comprobante creado exitosamente" });
    },
    onError: () => {
      toast({
        title: "Error al crear el comprobante",
        variant: "destructive",
      });
    },
  });

  const mutPagar = useMutation({
    mutationFn: pagarComprobante,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comprobantes"] });
      queryClient.invalidateQueries({ queryKey: ["facturacion-resumen"] });
      toast({ title: "Comprobante marcado como pagado" });
    },
    onError: () => {
      toast({ title: "Error al registrar el pago", variant: "destructive" });
    },
  });

  // ─── Forms ──────────────────────────────────────────────────────────────────

  const osForm = useForm<ObraSocialForm>({
    resolver: zodResolver(obraSocialSchema),
    defaultValues: {
      nombre: "",
      codigo: "",
      plan: "",
      porcentaje_cobertura: 0,
      copago_consulta: 0,
      notas: "",
    },
  });

  const compForm = useForm<ComprobanteForm>({
    resolver: zodResolver(comprobanteSchema),
    defaultValues: {
      paciente_id: "",
      obra_social_id: "",
      tipo: "recibo",
      concepto: "",
      notas: "",
      items: [{ descripcion: "", cantidad: 1, precio_unitario: 0 }],
    },
  });

  const { register: regComp, watch, setValue } = compForm;
  const watchedItems = watch("items");

  function addItem() {
    const current = watch("items");
    setValue("items", [
      ...current,
      { descripcion: "", cantidad: 1, precio_unitario: 0 },
    ]);
    setItemCount((c) => c + 1);
  }

  function removeItem(index: number) {
    const current = watch("items");
    if (current.length <= 1) return;
    setValue(
      "items",
      current.filter((_, i) => i !== index)
    );
    setItemCount((c) => c - 1);
  }

  const totalItems = watchedItems.reduce(
    (acc, item) => acc + (item.cantidad || 0) * (item.precio_unitario || 0),
    0
  );

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header title="Facturación" />
        <main className="flex-1 overflow-y-auto p-6">
          {/* Tabs */}
          <div className="flex gap-1 mb-6 border-b border-gray-200">
            {(
              [
                {
                  id: "comprobantes",
                  label: "Comprobantes",
                  icon: Receipt,
                },
                {
                  id: "obras_sociales",
                  label: "Obras Sociales",
                  icon: Building2,
                },
                { id: "resumen", label: "Resumen", icon: BarChart3 },
              ] as { id: Tab; label: string; icon: React.ElementType }[]
            ).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
                  activeTab === id
                    ? "border-primary-600 text-primary-700"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>

          {/* ── Tab: Comprobantes ─────────────────────────────────────── */}
          {activeTab === "comprobantes" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Select
                    value={filtroEstado}
                    onValueChange={setFiltroEstado}
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="todos">Todos</SelectItem>
                      <SelectItem value="pendiente">Pendiente</SelectItem>
                      <SelectItem value="pagado">Pagado</SelectItem>
                      <SelectItem value="cancelado">Cancelado</SelectItem>
                      <SelectItem value="anulado">Anulado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={() => setShowNuevoComprobante(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Nuevo Comprobante
                </Button>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {loadingComprobantes ? (
                  <div className="p-8 text-center text-gray-500">
                    Cargando comprobantes...
                  </div>
                ) : comprobantes.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    No hay comprobantes para mostrar.
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">
                          Número
                        </th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">
                          Tipo
                        </th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">
                          Concepto
                        </th>
                        <th className="px-4 py-3 text-right font-medium text-gray-600">
                          Monto
                        </th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">
                          Estado
                        </th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">
                          Fecha
                        </th>
                        <th className="px-4 py-3" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {comprobantes.map((c) => (
                        <tr key={c.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-mono text-xs text-gray-700">
                            {c.numero_comprobante}
                          </td>
                          <td className="px-4 py-3 text-gray-700">
                            {tipoLabel[c.tipo] ?? c.tipo}
                          </td>
                          <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                            {c.concepto}
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-gray-800">
                            {formatMoney(c.monto_total)}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={cn(
                                "inline-flex px-2 py-0.5 rounded-full text-xs font-medium",
                                estadoBadge[c.estado] ??
                                  "bg-gray-100 text-gray-600"
                              )}
                            >
                              {c.estado}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500 text-xs">
                            {new Date(c.fecha_emision).toLocaleDateString(
                              "es-AR"
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {c.estado === "pendiente" && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => mutPagar.mutate(c.id)}
                                disabled={mutPagar.isPending}
                              >
                                <CheckCircle className="h-3.5 w-3.5 mr-1" />
                                Pagar
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {/* ── Tab: Obras Sociales ───────────────────────────────────── */}
          {activeTab === "obras_sociales" && (
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button onClick={() => setShowNuevaOS(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Nueva OS
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {obras.map((os) => (
                  <div
                    key={os.id}
                    className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-gray-800">
                          {os.nombre}
                        </h3>
                        <p className="text-xs text-gray-500 font-mono">
                          {os.codigo}
                          {os.plan ? ` — ${os.plan}` : ""}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "text-xs px-2 py-0.5 rounded-full font-medium",
                          os.activa
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        )}
                      >
                        {os.activa ? "Activa" : "Inactiva"}
                      </span>
                    </div>
                    <div className="flex gap-4 text-sm text-gray-600">
                      <span>
                        <span className="font-medium">
                          {os.porcentaje_cobertura}%
                        </span>{" "}
                        cobertura
                      </span>
                      <span>
                        Copago:{" "}
                        <span className="font-medium">
                          {formatMoney(os.copago_consulta)}
                        </span>
                      </span>
                    </div>
                    {os.notas && (
                      <p className="mt-2 text-xs text-gray-400 line-clamp-2">
                        {os.notas}
                      </p>
                    )}
                  </div>
                ))}
                {obras.length === 0 && (
                  <p className="col-span-3 text-center text-gray-500 py-8">
                    No hay obras sociales registradas.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── Tab: Resumen ──────────────────────────────────────────── */}
          {activeTab === "resumen" && (
            <div className="space-y-6">
              {resumen ? (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
                      <p className="text-sm text-gray-500 mb-1">
                        Total facturado hoy
                      </p>
                      <p className="text-2xl font-bold text-gray-800">
                        {formatMoney(resumen.monto_total)}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {resumen.total_comprobantes} comprobante
                        {resumen.total_comprobantes !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-green-200 p-5 shadow-sm">
                      <p className="text-sm text-gray-500 mb-1">Cobrado</p>
                      <p className="text-2xl font-bold text-green-700">
                        {formatMoney(resumen.monto_cobrado)}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-yellow-200 p-5 shadow-sm">
                      <p className="text-sm text-gray-500 mb-1">Pendiente</p>
                      <p className="text-2xl font-bold text-yellow-700">
                        {formatMoney(resumen.monto_pendiente)}
                      </p>
                    </div>
                  </div>

                  <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                    <div className="px-5 py-4 border-b border-gray-100">
                      <h3 className="font-semibold text-gray-800">
                        Por obra social
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-50">
                      {resumen.por_obra_social.map((row, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between px-5 py-3 text-sm"
                        >
                          <span className="text-gray-700">{row.nombre}</span>
                          <div className="flex gap-6 text-right">
                            <span className="text-gray-500">
                              {row.cantidad} comp.
                            </span>
                            <span className="font-medium text-gray-800">
                              {formatMoney(row.monto)}
                            </span>
                          </div>
                        </div>
                      ))}
                      {resumen.por_obra_social.length === 0 && (
                        <p className="px-5 py-4 text-gray-500 text-sm">
                          Sin datos para el período.
                        </p>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center text-gray-500 py-12">
                  Cargando resumen...
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* ── Modal: Nueva Obra Social ──────────────────────────────────── */}
      <Dialog open={showNuevaOS} onOpenChange={setShowNuevaOS}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nueva Obra Social</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={osForm.handleSubmit((d) => mutCreateOS.mutate(d))}
            className="space-y-3"
          >
            <div>
              <label className="text-sm font-medium text-gray-700">
                Nombre *
              </label>
              <Input {...osForm.register("nombre")} placeholder="OSDE" />
              {osForm.formState.errors.nombre && (
                <p className="text-xs text-red-500 mt-1">
                  {osForm.formState.errors.nombre.message}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Código *
                </label>
                <Input
                  {...osForm.register("codigo")}
                  placeholder="OSDE-210"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Plan
                </label>
                <Input {...osForm.register("plan")} placeholder="210" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Cobertura (%)
                </label>
                <Input
                  type="number"
                  step="0.1"
                  {...osForm.register("porcentaje_cobertura")}
                  placeholder="70"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Copago ($)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  {...osForm.register("copago_consulta")}
                  placeholder="500"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">
                Notas
              </label>
              <Input {...osForm.register("notas")} placeholder="Notas opcionales" />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowNuevaOS(false)}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={mutCreateOS.isPending}>
                {mutCreateOS.isPending ? "Guardando..." : "Crear"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Modal: Nuevo Comprobante ─────────────────────────────────── */}
      <Dialog
        open={showNuevoComprobante}
        onOpenChange={setShowNuevoComprobante}
      >
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nuevo Comprobante</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={compForm.handleSubmit((d) =>
              mutCreateComprobante.mutate(d)
            )}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Paciente ID *
                </label>
                <Input
                  {...regComp("paciente_id")}
                  placeholder="UUID del paciente"
                />
                {compForm.formState.errors.paciente_id && (
                  <p className="text-xs text-red-500 mt-1">
                    {compForm.formState.errors.paciente_id.message}
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Tipo *
                </label>
                <Select
                  onValueChange={(v) =>
                    setValue(
                      "tipo",
                      v as "factura_a" | "factura_b" | "recibo" | "orden"
                    )
                  }
                  defaultValue="recibo"
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="recibo">Recibo</SelectItem>
                    <SelectItem value="factura_a">Factura A</SelectItem>
                    <SelectItem value="factura_b">Factura B</SelectItem>
                    <SelectItem value="orden">Orden</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Obra Social
              </label>
              <Select
                onValueChange={(v) =>
                  setValue("obra_social_id", v === "sin-os" ? "" : v)
                }
                defaultValue="sin-os"
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sin obra social" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sin-os">Sin obra social (particular)</SelectItem>
                  {obras.map((os) => (
                    <SelectItem key={os.id} value={os.id}>
                      {os.nombre} — {os.codigo}
                      {os.plan ? ` (${os.plan})` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Concepto *
              </label>
              <Input
                {...regComp("concepto")}
                placeholder="Descripción del servicio"
              />
              {compForm.formState.errors.concepto && (
                <p className="text-xs text-red-500 mt-1">
                  {compForm.formState.errors.concepto.message}
                </p>
              )}
            </div>

            {/* Ítems */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Ítems *
                </label>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={addItem}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Agregar ítem
                </Button>
              </div>
              <div className="space-y-2">
                {watchedItems.map((_, index) => (
                  <div
                    key={index}
                    className="grid grid-cols-12 gap-2 items-center"
                  >
                    <div className="col-span-5">
                      <Input
                        {...regComp(`items.${index}.descripcion`)}
                        placeholder="Descripción"
                      />
                    </div>
                    <div className="col-span-2">
                      <Input
                        type="number"
                        step="0.01"
                        {...regComp(`items.${index}.cantidad`)}
                        placeholder="Cant."
                      />
                    </div>
                    <div className="col-span-3">
                      <Input
                        type="number"
                        step="0.01"
                        {...regComp(`items.${index}.precio_unitario`)}
                        placeholder="Precio"
                      />
                    </div>
                    <div className="col-span-2 text-right text-xs text-gray-500">
                      {formatMoney(
                        (watchedItems[index]?.cantidad ?? 0) *
                          (watchedItems[index]?.precio_unitario ?? 0)
                      )}
                      {watchedItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeItem(index)}
                          className="ml-2 text-red-400 hover:text-red-600"
                          aria-label="Eliminar ítem"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-right text-sm font-semibold text-gray-700">
                Total: {formatMoney(totalItems)}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Notas
              </label>
              <Input {...regComp("notas")} placeholder="Notas opcionales" />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowNuevoComprobante(false)}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={mutCreateComprobante.isPending}>
                {mutCreateComprobante.isPending ? "Creando..." : "Crear comprobante"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
