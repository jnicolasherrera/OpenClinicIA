"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { agenda } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SalaEsperaItem } from "@/lib/types";
import { Clock, Users, Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";

function getTiempoColor(minutos: number): string {
  if (minutos < 15) return "text-green-600 bg-green-50";
  if (minutos < 30) return "text-yellow-600 bg-yellow-50";
  return "text-red-600 bg-red-50";
}

function getTiempoBadgeVariant(
  minutos: number
): "default" | "secondary" | "destructive" | "outline" {
  if (minutos < 15) return "secondary";
  if (minutos < 30) return "outline";
  return "destructive";
}

interface SalaEsperaItemCardProps {
  item: SalaEsperaItem;
  onLlamar: (turnoId: string) => void;
  isLlamando: boolean;
}

function SalaEsperaItemCard({
  item,
  onLlamar,
  isLlamando,
}: SalaEsperaItemCardProps) {
  return (
    <div className="p-3 rounded-lg border border-gray-100 bg-white hover:border-gray-200 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate">
            {item.paciente_nombre}
          </p>
          <p className="text-xs text-gray-500 truncate">
            Dr. {item.medico_nombre}
          </p>
        </div>
        <span className="text-xs font-mono text-gray-600 flex-shrink-0 bg-gray-100 px-1.5 py-0.5 rounded">
          {item.hora_turno}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div
          className={cn(
            "flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full",
            getTiempoColor(item.tiempo_espera_minutos)
          )}
        >
          <Clock className="h-3 w-3" />
          <span>
            {item.tiempo_espera_minutos === 0
              ? "Ahora"
              : `${item.tiempo_espera_minutos} min`}
          </span>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() => onLlamar(item.turno_id)}
          disabled={isLlamando}
          className="h-6 text-xs px-2 text-primary-600 border-primary-200 hover:bg-primary-50"
        >
          <Bell className="h-3 w-3 mr-1" />
          Llamar
        </Button>
      </div>
    </div>
  );
}

export function SalaEspera() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["sala-espera"],
    queryFn: () => agenda.getSalaEspera(),
    refetchInterval: 30 * 1000,
  });

  const handleLlamar = async (turnoId: string) => {
    try {
      await agenda.updateTurno(turnoId, { estado: "en_atencion" });
      await queryClient.invalidateQueries({ queryKey: ["sala-espera"] });
      toast({
        title: "Paciente llamado",
        description: "El paciente fue derivado a atención.",
      });
    } catch {
      toast({
        title: "Error",
        description: "No se pudo actualizar el estado del turno.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white rounded-t-xl">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-700">Sala de Espera</h3>
        </div>
        <Badge
          variant={items.length > 0 ? "default" : "secondary"}
          className={cn(
            "text-xs",
            items.length > 0 && "bg-primary-600 text-white"
          )}
        >
          {items.length}
        </Badge>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-20 rounded-lg bg-gray-200 animate-pulse"
              />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-10 text-gray-400">
            <Users className="h-10 w-10 mb-2 opacity-30" />
            <p className="text-xs text-center">
              No hay pacientes en sala de espera
            </p>
          </div>
        ) : (
          items.map((item) => (
            <SalaEsperaItemCard
              key={item.turno_id}
              item={item}
              onLlamar={handleLlamar}
              isLlamando={false}
            />
          ))
        )}
      </div>

      <div className="px-4 py-2 border-t border-gray-200 bg-white rounded-b-xl">
        <p className="text-xs text-gray-400 text-center">
          Actualiza cada 30 segundos
        </p>
      </div>
    </div>
  );
}
