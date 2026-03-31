"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { pacientes as pacientesApi } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Paciente, Episodio } from "@/lib/types";
import { Search, User, FileText, Calendar } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

function PacienteCard({
  paciente,
  onClick,
}: {
  paciente: Paciente;
  onClick: (p: Paciente) => void;
}) {
  return (
    <button
      onClick={() => onClick(paciente)}
      className="w-full text-left p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-all bg-white shadow-sm"
    >
      <div className="flex items-start gap-3">
        <div className="bg-primary-100 text-primary-700 rounded-full p-2 flex-shrink-0">
          <User className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold text-gray-800 truncate">
              {paciente.apellido}, {paciente.nombre}
            </p>
            <Badge variant="secondary" className="text-xs flex-shrink-0">
              #{paciente.numero_historia}
            </Badge>
          </div>
          <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs text-gray-500">
            <span>DNI: {paciente.dni}</span>
            <span>Tel: {paciente.telefono}</span>
            <span>
              Nac:{" "}
              {format(new Date(paciente.fecha_nacimiento), "dd/MM/yyyy", {
                locale: es,
              })}
            </span>
            {paciente.obra_social && (
              <span className="truncate">OS: {paciente.obra_social}</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

function HistoriaClinicaModal({
  paciente,
  open,
  onClose,
}: {
  paciente: Paciente | null;
  open: boolean;
  onClose: () => void;
}) {
  const { data: episodios = [], isLoading } = useQuery({
    queryKey: ["historia", paciente?.id],
    queryFn: () => pacientesApi.getHistoria(paciente!.id),
    enabled: open && !!paciente,
  });

  if (!paciente) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-600" />
            Historia Clínica — {paciente.apellido}, {paciente.nombre}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 gap-3 p-4 bg-gray-50 rounded-lg mb-4 text-sm">
            <div>
              <span className="text-gray-500">N° Historia:</span>{" "}
              <span className="font-medium">{paciente.numero_historia}</span>
            </div>
            <div>
              <span className="text-gray-500">DNI:</span>{" "}
              <span className="font-medium">{paciente.dni}</span>
            </div>
            <div>
              <span className="text-gray-500">Teléfono:</span>{" "}
              <span className="font-medium">{paciente.telefono}</span>
            </div>
            {paciente.email && (
              <div>
                <span className="text-gray-500">Email:</span>{" "}
                <span className="font-medium">{paciente.email}</span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Nacimiento:</span>{" "}
              <span className="font-medium">
                {format(new Date(paciente.fecha_nacimiento), "dd/MM/yyyy", {
                  locale: es,
                })}
              </span>
            </div>
            {paciente.obra_social && (
              <div>
                <span className="text-gray-500">Obra Social:</span>{" "}
                <span className="font-medium">{paciente.obra_social}</span>
              </div>
            )}
          </div>

          <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Episodios clínicos
          </h3>

          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-24 rounded-lg bg-gray-100 animate-pulse" />
              ))}
            </div>
          ) : episodios.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No hay episodios registrados en la historia clínica.
            </p>
          ) : (
            <div className="space-y-3">
              {episodios.map((episodio: Episodio) => (
                <div
                  key={episodio.id}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-gray-800">
                      {episodio.motivo_consulta}
                    </p>
                    <span className="text-xs text-gray-500">
                      {format(new Date(episodio.fecha), "dd/MM/yyyy", {
                        locale: es,
                      })}
                    </span>
                  </div>
                  {episodio.diagnostico && (
                    <p className="text-sm text-gray-600 mb-2">
                      <span className="font-medium">Diagnóstico:</span>{" "}
                      {episodio.diagnostico}
                    </p>
                  )}
                  {(episodio.soap_subjetivo ||
                    episodio.soap_objetivo ||
                    episodio.soap_assessment ||
                    episodio.soap_plan) && (
                    <div className="mt-2 pt-2 border-t border-gray-100 grid grid-cols-2 gap-2 text-xs">
                      {episodio.soap_subjetivo && (
                        <div>
                          <p className="font-semibold text-gray-500 uppercase tracking-wide">
                            S
                          </p>
                          <p className="text-gray-700">{episodio.soap_subjetivo}</p>
                        </div>
                      )}
                      {episodio.soap_objetivo && (
                        <div>
                          <p className="font-semibold text-gray-500 uppercase tracking-wide">
                            O
                          </p>
                          <p className="text-gray-700">{episodio.soap_objetivo}</p>
                        </div>
                      )}
                      {episodio.soap_assessment && (
                        <div>
                          <p className="font-semibold text-gray-500 uppercase tracking-wide">
                            A
                          </p>
                          <p className="text-gray-700">
                            {episodio.soap_assessment}
                          </p>
                        </div>
                      )}
                      {episodio.soap_plan && (
                        <div>
                          <p className="font-semibold text-gray-500 uppercase tracking-wide">
                            P
                          </p>
                          <p className="text-gray-700">{episodio.soap_plan}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <DialogFooter className="pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function PacientesPage() {
  const [searchInput, setSearchInput] = useState("");
  const [selectedPaciente, setSelectedPaciente] = useState<Paciente | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const debouncedSearch = useDebounce(searchInput, 300);

  const {
    data: resultados = [],
    isLoading,
    isFetching,
  } = useQuery({
    queryKey: ["pacientes-search", debouncedSearch],
    queryFn: () => pacientesApi.searchPacientes(debouncedSearch),
    enabled: debouncedSearch.length >= 2,
  });

  const handlePacienteClick = useCallback((paciente: Paciente) => {
    setSelectedPaciente(paciente);
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedPaciente(null);
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title="Pacientes" />

        <main className="flex-1 overflow-y-auto p-6">
          <Card className="border-0 shadow-sm mb-6">
            <CardContent className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  className="pl-9"
                  placeholder="Buscar por nombre, apellido o DNI (mínimo 2 caracteres)..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {debouncedSearch.length < 2 ? (
            <div className="text-center py-16 text-gray-400">
              <Search className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                Ingresá al menos 2 caracteres para buscar pacientes.
              </p>
            </div>
          ) : isLoading || isFetching ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-20 rounded-lg bg-gray-200 animate-pulse"
                />
              ))}
            </div>
          ) : resultados.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <User className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                No se encontraron pacientes para "{debouncedSearch}".
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-500 mb-3">
                {resultados.length} resultado{resultados.length !== 1 ? "s" : ""}{" "}
                encontrado{resultados.length !== 1 ? "s" : ""}
              </p>
              <div className="space-y-2">
                {resultados.map((paciente) => (
                  <PacienteCard
                    key={paciente.id}
                    paciente={paciente}
                    onClick={handlePacienteClick}
                  />
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      <HistoriaClinicaModal
        paciente={selectedPaciente}
        open={isModalOpen}
        onClose={handleCloseModal}
      />
    </div>
  );
}
