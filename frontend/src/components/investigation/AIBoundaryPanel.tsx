import React from "react";
import { Check, X, Cpu } from "lucide-react";

export const AIBoundaryPanel: React.FC = () => {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
      <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-indigo-600" />
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            AI Investigator Safety & Control Boundary
          </h4>
        </div>
        <span className="text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-200">
          ACCESS: STRICTLY READ-ONLY
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        {/* Permitted Read-Only Capabilities */}
        <div className="space-y-1.5 p-3 bg-emerald-50/30 border border-emerald-100 rounded-md">
          <span className="font-semibold text-emerald-900 text-[11px] block">
            PERMITTED READ-ONLY CAPABILITIES
          </span>
          <ul className="space-y-1 text-emerald-800 text-[11px]">
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Lookup order checkout details</span>
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Lookup payment gateway records</span>
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Lookup bank settlement payouts & UTRs</span>
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Lookup tax invoice status & amounts</span>
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Corroborate multi-entity evidence chains</span>
            </li>
          </ul>
        </div>

        {/* Prohibited Write Operations */}
        <div className="space-y-1.5 p-3 bg-rose-50/30 border border-rose-100 rounded-md">
          <span className="font-semibold text-rose-900 text-[11px] block">
            PROHIBITED FINANCIAL MUTATIONS
          </span>
          <ul className="space-y-1 text-rose-800 text-[11px]">
            <li className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Cannot modify transaction records</span>
            </li>
            <li className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Cannot alter accounting ledger balances</span>
            </li>
            <li className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Cannot override deterministic policy rules</span>
            </li>
            <li className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Cannot issue refunds or initiate payouts</span>
            </li>
            <li className="flex items-center gap-1.5">
              <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Cannot approve high-risk exceptions</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

