"use client";

import { format, isSameDay } from "date-fns";
import { es } from "date-fns/locale";
import type { Turno } from "@/lib/types";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface CalendarioSemanalProps {
  turnos: Turno[];
  weekDays: Date[];
  onTurnoClick: (turno: Turno) => void;
  onPrevWeek: () => void;
  onNextWeek: () => void;
}

const estadoConfig: Record<
  Turno["estado"],
  { bg: string; text: string; dot: string }
> = {
  programado: {
    bg: "bg-blue-50 hover:bg-blue-100",
    text: "text-blue-800",
    dot: "bg-blue-400",
  },
  confirmado: {
    bg: "bg-green-50 hover:bg-green-100",
    text: "text-green-800",
    dot: "bg-green-400",
  },
  en_sala: {
    bg: "bg-yellow-50 hover:bg-yellow-100",
    text: "text-yellow-800",
    dot: "bg-yellow-400",
  },
  en_atencion: {
    bg: "bg-purple-50 hover:bg-purple-100",
    text: "text-purple-800",
    dot: "bg-purple-400",
  },
  completado: {
    bg: "bg-gray-50 hover:bg-gray-100",
    text: "text-gray-600",
    dot: "bg-gray-400",
  },
  cancelado: {
    bg: "bg-red-50 hover:bg-red-100",
    text: "text-red-700",
    dot: "bg-red-400",
  },
  ausente: {
    bg: "bg-orange-50 hover:bg-orange-100",
    text: "text-orange-700",
    dot: "bg-orange-400",
  },
};

export function CalendarioSemanal({
  turnos,
  weekDays,
  onTurnoClick,
  onPrevWeek,
  onNextWeek,
}: CalendarioSemanalProps) {
  const today = new Date();

  const getTurnosForDay = (day: Date): Turno[] => {
    return turnos
      .filter((turno) => isSameDay(new Date(turno.fecha_hora), day))
      .sort(
        (a, b) =>
          new Date(a.fecha_hora).getTime() - new Date(b.fecha_hora).getTime()
      );
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <button
          onClick={onPrevWeek}
          className="p-1.5 rounded-md hover:bg-gray-200 transition-colors text-gray-500 hover:text-gray-700"
          aria-label="Semana anterior"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium text-gray-700">
          {format(weekDays[0], "d 'de' MMM", { locale: es })} —{" "}
          {format(weekDays[weekDays.length - 1], "d 'de' MMM yyyy", {
            locale: es,
          })}
        </span>
        <button
          onClick={onNextWeek}
          className="p-1.5 rounded-md hover:bg-gray-200 transition-colors text-gray-500 hover:text-gray-700"
          aria-label="Semana siguiente"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 divide-x divide-gray-100 overflow-x-auto">
        {weekDays.map((day) => {
          const dayTurnos = getTurnosForDay(day);
          const isToday = isSameDay(day, today);

          return (
            <div key={day.toISOString()} className="min-w-[120px] flex flex-col">
              <div
                className={cn(
                  "px-2 py-2 text-center border-b border-gray-100",
                  isToday ? "bg-primary-50" : "bg-gray-50"
                )}
              >
                <p
                  className={cn(
                    "text-xs font-medium uppercase tracking-wide",
                    isToday ? "text-primary-600" : "text-gray-500"
                  )}
                >
                  {format(day, "EEE", { locale: es })}
                </p>
                <p
                  className={cn(
                    "text-lg font-bold mt-0.5",
                    isToday ? "text-primary-700" : "text-gray-800"
                  )}
                >
                  {format(day, "d")}
                </p>
                {dayTurnos.length > 0 && (
                  <span className="text-xs text-gray-400">
                    {dayTurnos.length} turno{dayTurnos.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>

              <div className="flex-1 p-1.5 space-y-1 min-h-[200px]">
                {dayTurnos.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-xs text-gray-300">Sin turnos</p>
                  </div>
                ) : (
                  dayTurnos.map((turno) => {
                    const config = estadoConfig[turno.estado];
                    return (
                      <button
                        key={turno.id}
                        onClick={() => onTurnoClick(turno)}
                        className={cn(
                          "w-full text-left px-2 py-1.5 rounded-md transition-colors",
                          config.bg
                        )}
                      >
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span
                            className={cn(
                              "w-1.5 h-1.5 rounded-full flex-shrink-0",
                              config.dot
                            )}
                          />
                          <span
                            className={cn(
                              "text-xs font-semibold",
                              config.text
                            )}
                          >
                            {format(new Date(turno.fecha_hora), "HH:mm")}
                          </span>
                        </div>
                        <p
                          className={cn(
                            "text-xs truncate font-medium",
                            config.text
                          )}
                        >
                          {turno.paciente_nombre ?? "Paciente"}
                        </p>
                        <p className="text-xs text-gray-400 truncate">
                          {turno.estado.replace("_", " ")}
                        </p>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
