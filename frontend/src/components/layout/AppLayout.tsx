import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  ShieldCheck,
  LayoutDashboard,
  Layers,
  SearchCode,
  RefreshCw,
  Lock,
} from "lucide-react";
import { api } from "../../services/api";

export const AppLayout: React.FC = () => {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const location = useLocation();

  const checkHealth = async () => {
    try {
      const res = await api.getHealth();
      setApiOnline(res.status === "healthy");
    } catch {
      setApiOnline(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    const p = location.pathname;
    if (p === "/" || p === "/dashboard") return "Reconciliation Overview";
    if (p.startsWith("/cases/") && p !== "/cases") return "Case Details & Transaction Chain";
    if (p.startsWith("/cases")) return "Operational Case Explorer";
    if (p.startsWith("/investigations/") && p !== "/investigations") return "Investigation Finding & Audit Trace";
    if (p.startsWith("/investigations")) return "AI Investigation Registry";
    return "Operations Console";
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Left Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between border-r border-slate-800 shrink-0 select-none">
        <div>
          {/* Brand Header */}
          <div className="p-5 border-b border-slate-800 flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-sky-500 text-slate-950 flex items-center justify-center font-bold shadow-xs">
              <ShieldCheck className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-wider text-white">RECONGUARD</h1>
              <p className="text-[11px] text-slate-400 font-medium">Payment Operations</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-slate-800 text-white border-l-2 border-sky-400 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4 text-slate-400" />
              Overview
            </NavLink>

            <NavLink
              to="/cases"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-slate-800 text-white border-l-2 border-sky-400 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`
              }
            >
              <Layers className="w-4 h-4 text-slate-400" />
              Cases
            </NavLink>

            <NavLink
              to="/investigations"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-slate-800 text-white border-l-2 border-sky-400 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`
              }
            >
              <SearchCode className="w-4 h-4 text-slate-400" />
              Investigations
            </NavLink>
          </nav>
        </div>

        {/* Lower System Status */}
        <div className="p-4 border-t border-slate-800 text-[11px] space-y-2 bg-slate-950/40">
          <div className="flex items-center justify-between text-slate-400">
            <span className="font-medium">Backend API</span>
            {apiOnline === null ? (
              <span className="flex items-center gap-1 text-slate-500">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-pulse"></span>
                Checking...
              </span>
            ) : apiOnline ? (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                Live (FastAPI)
              </span>
            ) : (
              <span className="flex items-center gap-1 text-rose-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                Offline
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-slate-400 pt-1 border-t border-slate-800/60">
            <Lock className="w-3 h-3 text-sky-400 shrink-0" />
            <span className="text-[10px] text-slate-400">Read-Only Engine • 0 Write Tools</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 tracking-tight">{getPageTitle()}</h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
              <span className="text-slate-400">Engine:</span>
              <span className="font-medium text-slate-800">1,000 Cases Reconciled</span>
            </div>

            <button
              onClick={() => {
                checkHealth();
                window.location.reload();
              }}
              title="Refresh console state"
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Scrollable Page Outlet */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

