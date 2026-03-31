"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, startOfWeek, endOfWeek, eachDayOfInterval } from "date-fns";
import { agenda } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { CalendarioSemanal } from "@/components/agenda/CalendarioSemanal";
import { SalaEspera } from "@/components/agenda/SalaEspera";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Turno } from "@/lib/types";
import { Plus } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const turnoSchema = z.object({
  paciente_id: z.string().min(1, "El paciente es requerido"),
  medico_id: z.string().min(1, "El médico es requerido"),
  fecha_hora: z.string().min(1, "La fecha y hora son requeridas"),
  duracion_minutos: z.coerce
    .number()
    .min(5, "Mínimo 5 minutos")
    .max(240, "Máximo 240 minutos"),
  motivo: z.string().optional(),
});

type TurnoFormValues = z.infer<typeof turnoSchema>;

export default function AgendaPage() {
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTurno, setSelectedTurno] = useState<Turno | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const weekDays = eachDayOfInterval({
    start: currentWeekStart,
    end: endOfWeek(currentWeekStart, { weekStartsOn: 1 }),
  });

  const startDateStr = format(weekDays[0], "yyyy-MM-dd");
  const endDateStr = format(weekDays[weekDays.length - 1], "yyyy-MM-dd");

  const { data: turnos = [], isLoading } = useQuery({
    queryKey: ["turnos-semana", startDateStr, endDateStr],
    queryFn: async () => {
      const allDayTurnos = await Promise.all(
        weekDays.map((day) => agenda.getTurnos(format(day, "yyyy-MM-dd")))
      );
      return allDayTurnos.flat();
    },
    refetchInterval: 60 * 1000,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TurnoFormValues>({
    resolver: zodResolver(turnoSchema),
    defaultValues: {
      duracion_minutos: 30,
    },
  });

  const onSubmit = async (data: TurnoFormValues) => {
    try {
      await agenda.createTurno(data);
      await queryClient.invalidateQueries({
        queryKey: ["turnos-semana"],
      });
      toast({
        title: "Turno creado",
        description: "El turno fue agendado correctamente.",
      });
      setIsModalOpen(false);
      reset();
    } catch {
      toast({
        title: "Error",
        description: "No se pudo crear el turno. Intentá de nuevo.",
        variant: "destructive",
      });
    }
  };

  const handleTurnoClick = (turno: Turno) => {
    setSelectedTurno(turno);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title="Agenda" />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-700">
              Semana del {format(weekDays[0], "d MMM")} al{" "}
              {format(weekDays[weekDays.length - 1], "d MMM yyyy")}
            </h2>
            <Button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white"
            >
              <Plus className="h-4 w-4" />
              Nuevo Turno
            </Button>
          </div>

          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              {isLoading ? (
                <div className="h-96 rounded-xl bg-gray-200 animate-pulse" />
              ) : (
                <CalendarioSemanal
                  turnos={turnos}
                  weekDays={weekDays}
                  onTurnoClick={handleTurnoClick}
                  onPrevWeek={() =>
                    setCurrentWeekStart(
                      (prev) =>
                        new Date(prev.getTime() - 7 * 24 * 60 * 60 * 1000)
                    )
                  }
                  onNextWeek={() =>
                    setCurrentWeekStart(
                      (prev) =>
                        new Date(prev.getTime() + 7 * 24 * 60 * 60 * 1000)
                    )
                  }
                />
              )}
            </div>

            <div className="w-80 flex-shrink-0">
              <SalaEspera />
            </div>
          </div>
        </main>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nuevo Turno</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Paciente
              </label>
              <Input
                placeholder="ID del paciente"
                {...register("paciente_id")}
                className={errors.paciente_id ? "border-red-500" : ""}
              />
              {errors.paciente_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.paciente_id.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Médico
              </label>
              <Input
                placeholder="ID del médico"
                {...register("medico_id")}
                className={errors.medico_id ? "border-red-500" : ""}
              />
              {errors.medico_id && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.medico_id.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha y Hora
              </label>
              <Input
                type="datetime-local"
                {...register("fecha_hora")}
                className={errors.fecha_hora ? "border-red-500" : ""}
              />
              {errors.fecha_hora && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.fecha_hora.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Duración (minutos)
              </label>
              <Input
                type="number"
                min={5}
                max={240}
                step={5}
                {...register("duracion_minutos")}
                className={errors.duracion_minutos ? "border-red-500" : ""}
              />
              {errors.duracion_minutos && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.duracion_minutos.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Motivo (opcional)
              </label>
              <Input placeholder="Motivo de la consulta" {...register("motivo")} />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsModalOpen(false);
                  reset();
                }}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-primary-600 hover:bg-primary-700 text-white"
              >
                {isSubmitting ? "Guardando..." : "Guardar Turno"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={selectedTurno !== null}
        onOpenChange={() => setSelectedTurno(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Detalle del Turno</DialogTitle>
          </DialogHeader>
          {selectedTurno && (
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-gray-500">Paciente</p>
                  <p className="font-medium">
                    {selectedTurno.paciente_nombre ?? selectedTurno.paciente_id}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Médico</p>
                  <p className="font-medium">
                    {selectedTurno.medico_nombre ?? selectedTurno.medico_id}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Fecha y hora</p>
                  <p className="font-medium">
                    {format(
                      new Date(selectedTurno.fecha_hora),
                      "dd/MM/yyyy HH:mm"
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Duración</p>
                  <p className="font-medium">
                    {selectedTurno.duracion_minutos} min
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Estado</p>
                  <p className="font-medium capitalize">
                    {selectedTurno.estado.replace("_", " ")}
                  </p>
                </div>
                {selectedTurno.motivo && (
                  <div className="col-span-2">
                    <p className="text-gray-500">Motivo</p>
                    <p className="font-medium">{selectedTurno.motivo}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedTurno(null)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
