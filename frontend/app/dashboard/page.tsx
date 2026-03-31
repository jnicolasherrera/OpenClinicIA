"use client";

import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { agenda } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Turno } from "@/lib/types";
import { Calendar, Clock, CheckCircle, Users, AlertCircle } from "lucide-react";

const estadoColors: Record<Turno["estado"], string> = {
  programado: "bg-blue-100 text-blue-800",
  confirmado: "bg-green-100 text-green-800",
  en_sala: "bg-yellow-100 text-yellow-800",
  en_atencion: "bg-purple-100 text-purple-800",
  completado: "bg-gray-100 text-gray-800",
  cancelado: "bg-red-100 text-red-800",
  ausente: "bg-orange-100 text-orange-800",
};

export default function DashboardPage() {
  const today = format(new Date(), "yyyy-MM-dd");

  const {
    data: turnos = [],
    isLoading: turnosLoading,
  } = useQuery({
    queryKey: ["turnos", today],
    queryFn: () => agenda.getTurnos(today),
    refetchInterval: 60 * 1000,
  });

  const {
    data: salaEspera = [],
    isLoading: salaLoading,
  } = useQuery({
    queryKey: ["sala-espera"],
    queryFn: () => agenda.getSalaEspera(),
    refetchInterval: 60 * 1000,
  });

  const totalTurnos = turnos.length;
  const completados = turnos.filter((t) => t.estado === "completado").length;
  const enSala = salaEspera.length;
  const pendientes = turnos.filter(
    (t) => t.estado === "programado" || t.estado === "confirmado"
  ).length;

  const proximosTurnos = turnos
    .filter((t) => t.estado !== "cancelado" && t.estado !== "ausente")
    .slice(0, 5);

  const isLoading = turnosLoading || salaLoading;

  const metrics = [
    {
      title: "Total turnos hoy",
      value: totalTurnos,
      icon: Calendar,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      title: "Completados",
      value: completados,
      icon: CheckCircle,
      color: "text-green-600",
      bg: "bg-green-50",
    },
    {
      title: "En sala de espera",
      value: enSala,
      icon: Users,
      color: "text-yellow-600",
      bg: "bg-yellow-50",
    },
    {
      title: "Pendientes",
      value: pendientes,
      icon: AlertCircle,
      color: "text-orange-600",
      bg: "bg-orange-50",
    },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title="Dashboard" />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-700">
              {format(new Date(), "EEEE, d 'de' MMMM 'de' yyyy", { locale: es })}
            </h2>
            <p className="text-sm text-gray-500">Resumen del día</p>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-28 rounded-xl bg-gray-200 animate-pulse"
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {metrics.map((metric) => {
                const Icon = metric.icon;
                return (
                  <Card key={metric.title} className="border-0 shadow-sm">
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-500 mb-1">
                            {metric.title}
                          </p>
                          <p className="text-3xl font-bold text-gray-800">
                            {metric.value}
                          </p>
                        </div>
                        <div
                          className={`${metric.bg} ${metric.color} p-3 rounded-lg`}
                        >
                          <Icon className="h-6 w-6" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-500" />
                Próximos turnos
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="h-12 rounded-lg bg-gray-100 animate-pulse"
                    />
                  ))}
                </div>
              ) : proximosTurnos.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">
                  No hay turnos programados para hoy.
                </p>
              ) : (
                <div className="space-y-2">
                  {proximosTurnos.map((turno) => (
                    <div
                      key={turno.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-sm font-medium text-gray-700 w-16">
                          {format(new Date(turno.fecha_hora), "HH:mm")}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-800">
                            {turno.paciente_nombre ?? "Paciente"}
                          </p>
                          <p className="text-xs text-gray-500">
                            Dr. {turno.medico_nombre ?? "Médico"}
                          </p>
                        </div>
                      </div>
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full ${estadoColors[turno.estado]}`}
                      >
                        {turno.estado.replace("_", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
