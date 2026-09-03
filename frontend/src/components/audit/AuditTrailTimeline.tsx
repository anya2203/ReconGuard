import React from "react";
import {
  CheckCircle,
  Clock,
  Cpu,
  FileCheck,
  HelpCircle,
  Lock,
  Search,
  Shield,
  UserCheck,
  AlertTriangle,
} from "lucide-react";
import type { AuditEvent } from "../../types/api";
import { formatINR } from "../common/FormatMoney";

interface AuditTrailTimelineProps {
  events: AuditEvent[];
  isLoading?: boolean;
}

export const AuditTrailTimeline: React.FC<AuditTrailTimelineProps> = ({
  events,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs animate-pulse">
        <div className="h-5 bg-slate-200 rounded-sm w-48 mb-4"></div>
        <div className="space-y-4">
          <div className="h-16 bg-slate-100 rounded-md"></div>
          <div className="h-16 bg-slate-100 rounded-md"></div>
        </div>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs text-center text-slate-500">
        <Clock className="w-8 h-8 mx-auto text-slate-400 mb-2" />
        <p className="text-sm font-medium">No audit events recorded for this case yet.</p>
      </div>
    );
  }

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return ts;
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case "DETERMINISTIC":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Lock className="w-3 h-3 text-emerald-600" />
            DETERMINISTIC
          </span>
        );
      case "AI":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Cpu className="w-3 h-3 text-indigo-600" />
            AI INVESTIGATION
          </span>
        );
      case "HUMAN":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <UserCheck className="w-3 h-3 text-amber-600" />
            HUMAN CONTROL
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {source}
          </span>
        );
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case "RECONCILIATION_COMPLETED":
        return <FileCheck className="w-4 h-4 text-emerald-600" />;
      case "POLICY_DECISION":
        return <Shield className="w-4 h-4 text-slate-700" />;
      case "AI_INVESTIGATION_STARTED":
        return <Search className="w-4 h-4 text-indigo-600" />;
      case "AI_INVESTIGATION_COMPLETED":
        return <CheckCircle className="w-4 h-4 text-indigo-600" />;
      case "AI_INVESTIGATION_FAILED":
        return <AlertTriangle className="w-4 h-4 text-rose-600" />;
      case "HUMAN_REVIEW_REQUIRED":
        return <HelpCircle className="w-4 h-4 text-amber-600" />;
      default:
        return <Clock className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-slate-700" />
          <h3 className="text-sm font-semibold text-slate-900">Audit Trail & Financial Control Evidence</h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {events.length} immutable event{events.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-200">
        {events.map((evt, idx) => {
          const details = evt.details_json || {};
          const isLast = idx === events.length - 1;

          return (
            <div key={evt.audit_id || idx} className="relative group">
              {/* Timeline marker icon */}
              <div
                className={`absolute -left-[30px] top-0 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white shadow-xs ${
                  evt.source === "AI"
                    ? "border-indigo-500"
                    : evt.source === "HUMAN"
                    ? "border-amber-500"
                    : "border-emerald-500"
                }`}
              >
                {getActionIcon(evt.action)}
              </div>

              {/* Event card content */}
              <div
                className={`p-3.5 rounded-lg border text-sm transition-all ${
                  isLast
                    ? "bg-slate-50/80 border-slate-300 ring-1 ring-slate-200"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900 font-mono text-xs">
                      {evt.action}
                    </span>
                    {getSourceBadge(evt.source)}
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    {formatTime(evt.timestamp)}
                  </span>
                </div>

                <div className="text-xs text-slate-600 mt-1">
                  <span className="text-slate-500 font-mono">Actor:</span>{" "}
                  <span className="font-medium text-slate-800">{evt.actor}</span>
                </div>

                {/* Event specific details breakdown */}
                <div className="mt-2.5 pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
                  {details.decision !== undefined && details.decision !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Policy Decision:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {String(details.decision)}
                      </span>
                    </div>
                  )}

                  {typeof details.financial_impact === "number" && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Financial Exposure:</span>
                      <span className="font-semibold text-slate-900 font-mono">
                        {formatINR(Number(details.financial_impact))}
                      </span>
                    </div>
                  )}

                  {details.finding !== undefined && details.finding !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Corroborated Finding:</span>
                      <span className="font-semibold text-indigo-700 font-mono">
                        {String(details.finding)}
                      </span>
                    </div>
                  )}

                  {details.confidence !== undefined && details.confidence !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Confidence Score:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {(Number(details.confidence) * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}

                  {details.provider !== undefined && details.provider !== null && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">AI Provider:</span>
                      <span className="font-mono text-slate-700 uppercase">
                        {String(details.provider)}
                      </span>
                    </div>
                  )}

                  {details.reason !== undefined && details.reason !== null && (
                    <div className="mt-1 text-slate-700 bg-slate-50 p-2 rounded border border-slate-100">
                      <span className="font-medium text-slate-600">RATIONALE: </span>
                      {String(details.reason)}
                    </div>
                  )}

                  {details.recommendation !== undefined && details.recommendation !== null && (
                    <div className="mt-1 text-indigo-900 bg-indigo-50/50 p-2 rounded border border-indigo-100">
                      <span className="font-medium text-indigo-700">RECOMMENDATION: </span>
                      {String(details.recommendation)}
                    </div>
                  )}

                  {Array.isArray(details.tools_called) && details.tools_called.length > 0 && (
                    <div className="pt-1">
                      <span className="text-slate-500">Tools Consulted: </span>
                      <span className="font-mono text-slate-700">
                        {details.tools_called.map(String).join(" → ")}
                      </span>
                    </div>
                  )}

                  {details.required_desk !== undefined && details.required_desk !== null && (
                    <div className="flex items-center justify-between text-amber-800 font-medium pt-1">
                      <span>Assigned Operations Desk:</span>
                      <span className="font-mono text-amber-900">{String(details.required_desk)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
