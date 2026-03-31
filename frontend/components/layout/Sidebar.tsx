"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import {
  LayoutDashboard,
  Calendar,
  Users,
  FileText,
  Brain,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Receipt,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Agenda",
    href: "/agenda",
    icon: Calendar,
  },
  {
    label: "Pacientes",
    href: "/pacientes",
    icon: Users,
  },
  {
    label: "Historia Clínica",
    href: "/pacientes",
    icon: FileText,
  },
  {
    label: "IA Triaje",
    href: "/triaje",
    icon: Brain,
  },
  {
    label: "Facturación",
    href: "/facturacion",
    icon: Receipt,
  },
];

const rolLabels: Record<string, string> = {
  medico: "Médico/a",
  recepcion: "Recepción",
  admin: "Administrador/a",
  paciente: "Paciente",
};

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  return (
    <aside
      className={cn(
        "flex flex-col bg-gray-900 text-white transition-all duration-300 flex-shrink-0",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      <div className="flex items-center justify-between px-4 h-16 border-b border-gray-700">
        {sidebarOpen && (
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xl">🏥</span>
            <span className="font-bold text-white truncate">OpenClinicIA</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className={cn(
            "p-1.5 rounded-md hover:bg-gray-700 transition-colors text-gray-400 hover:text-white flex-shrink-0",
            !sidebarOpen && "mx-auto"
          )}
          aria-label={sidebarOpen ? "Cerrar sidebar" : "Abrir sidebar"}
        >
          {sidebarOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <li key={`${item.label}-${item.href}`}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary-600 text-white"
                      : "text-gray-300 hover:bg-gray-700 hover:text-white",
                    !sidebarOpen && "justify-center"
                  )}
                  title={!sidebarOpen ? item.label : undefined}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  {sidebarOpen && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-gray-700 p-3">
        {user && sidebarOpen && (
          <div className="mb-3 px-2 py-2 rounded-lg bg-gray-800">
            <p className="text-sm font-medium text-white truncate">
              {user.nombre} {user.apellido}
            </p>
            <p className="text-xs text-gray-400 truncate">
              {rolLabels[user.rol] ?? user.rol}
            </p>
            <p className="text-xs text-gray-500 truncate">{user.email}</p>
          </div>
        )}

        <button
          onClick={handleLogout}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:bg-red-900/40 hover:text-red-300 transition-colors",
            !sidebarOpen && "justify-center"
          )}
          title={!sidebarOpen ? "Cerrar sesión" : undefined}
        >
          <LogOut className="h-5 w-5 flex-shrink-0" />
          {sidebarOpen && <span>Cerrar sesión</span>}
        </button>
      </div>
    </aside>
  );
}
