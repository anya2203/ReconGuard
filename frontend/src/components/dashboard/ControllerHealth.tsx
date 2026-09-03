import React from "react";
import { CheckCircle2, ShieldCheck, Lock, Cpu, Database, Ban } from "lucide-react";

export const ControllerHealth: React.FC = () => {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-slate-800" />
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Finance Controller Health & Safety Invariants
          </h3>
        </div>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          ACTIVE / PROTECTED
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
        {/* 1. Reconciliation */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span>RECONCILIATION</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          </div>
          <div className="font-bold text-slate-900 font-mono">HEALTHY</div>
          <div className="text-[10px] text-slate-500">4 Matching Strategies</div>
        </div>

        {/* 2. Policy Engine */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span>POLICY ENGINE</span>
            <Lock className="w-3.5 h-3.5 text-emerald-600" />
          </div>
          <div className="font-bold text-emerald-700 font-mono">DETERMINISTIC</div>
          <div className="text-[10px] text-slate-500">12 Decision Branches</div>
        </div>

        {/* 3. AI Investigator */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span>AI INVESTIGATOR</span>
            <Cpu className="w-3.5 h-3.5 text-indigo-600" />
          </div>
          <div className="font-bold text-indigo-700 font-mono">READ-ONLY</div>
          <div className="text-[10px] text-slate-500">8 Inspection Tools</div>
        </div>

        {/* 4. Audit Trail */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span>AUDIT TRAIL</span>
            <Database className="w-3.5 h-3.5 text-emerald-600" />
          </div>
          <div className="font-bold text-slate-900 font-mono">ACTIVE</div>
          <div className="text-[10px] text-slate-500">Immutable / Append-Only</div>
        </div>

        {/* 5. Financial Writes */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-md space-y-1 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-500 text-[11px]">
            <span>FINANCIAL WRITES</span>
            <Ban className="w-3.5 h-3.5 text-rose-600" />
          </div>
          <div className="font-bold text-rose-700 font-mono">0 MUTATIONS</div>
          <div className="text-[10px] text-slate-500">Zero Write Authority</div>
        </div>
      </div>
    </div>
  );
};

