import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  Bot,
  UserCheck,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Layers,
} from "lucide-react";
import { api } from "../services/api";
import type { CaseSummary, DashboardSummary } from "../types/api";
import { Card } from "../components/common/Card";
import { DecisionBadge, PriorityBadge } from "../components/common/Badge";
import { FormatMoney, formatINR } from "../components/common/FormatMoney";
import { ErrorState, LoadingState } from "../components/common/States";

export const OverviewPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentCases, setRecentCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, casesRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getCases({ page: 1, page_size: 8, priority: "HIGH" }),
      ]);
      setSummary(sumRes);
      setRecentCases(casesRes.cases);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load dashboard data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Loading dashboard reconciliation metrics..." />;
  if (error || !summary) return <ErrorState message={error || "Dashboard data unavailable"} onRetry={loadData} />;

  const autoResolvePercent = ((summary.auto_resolved / summary.total_cases) * 100).toFixed(1);
  const aiPercent = ((summary.ai_investigation / summary.total_cases) * 100).toFixed(1);
  const humanPercent = ((summary.human_review / summary.total_cases) * 100).toFixed(1);
  const escalatePercent = ((summary.escalated / summary.total_cases) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Product Subtitle Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <h1 className="text-lg font-bold text-slate-900 tracking-tight">Reconciliation Overview</h1>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic matching first. AI investigation only for complex discrepancies. Zero financial mutations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/cases"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium transition-colors shadow-xs"
          >
            Explore 1,000 Cases
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Canonical Demo Scenarios Quick-Launcher Card */}
      <Card
        title="Curated Reconciliation Demo Scenarios"
        subtitle="Explore key operational archetypes across deterministic resolution, autonomous AI investigation, and dispute escalation"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {/* 1. Hero AI Case */}
          <Link
            to="/cases/CASE-000921"
            className="p-4 bg-sky-50/40 hover:bg-sky-50/80 border border-sky-200 rounded-md transition-all shadow-2xs group flex flex-col justify-between space-y-3"
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 bg-sky-100 text-sky-800 rounded font-mono font-bold text-[10px]">
                  HERO AI DEMO
                </span>
                <span className="text-xs font-mono font-bold text-sky-700">CASE-000921</span>
              </div>
              <h4 className="text-xs font-bold text-slate-900 group-hover:text-sky-900">Reference Mismatch / UTR Typo</h4>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Character transposition in bank UTR (<strong className="font-mono">...12</strong> vs <strong className="font-mono">...21</strong>). Uses 8 read-only tool calls to investigate and corroborate the reference mismatch.
              </p>
            </div>
            <div className="flex items-center justify-between text-[11px] text-sky-700 font-medium pt-2 border-t border-sky-100">
              <span>Decision: AI_INVESTIGATION</span>
              <span className="flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                Inspect Case →
              </span>
            </div>
          </Link>

          {/* 2. Exact Match Auto-Resolve */}
          <Link
            to="/cases/CASE-000001"
            className="p-4 bg-emerald-50/40 hover:bg-emerald-50/80 border border-emerald-200 rounded-md transition-all shadow-2xs group flex flex-col justify-between space-y-3"
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-mono font-bold text-[10px]">
                  EXACT MATCH BASELINE
                </span>
                <span className="text-xs font-mono font-bold text-emerald-700">CASE-000001</span>
              </div>
              <h4 className="text-xs font-bold text-slate-900 group-hover:text-emerald-900">Clean 1:1 Auto-Resolution</h4>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Standard high-volume payment matching. Reconciled instantly by deterministic ExactMatcher with 100% confidence.
              </p>
            </div>
            <div className="flex items-center justify-between text-[11px] text-emerald-700 font-medium pt-2 border-t border-emerald-100">
              <span>Decision: AUTO_RESOLVE</span>
              <span className="flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                Inspect Case →
              </span>
            </div>
          </Link>

          {/* 3. Dispute Escalation */}
          <Link
            to="/cases/CASE-000853"
            className="p-4 bg-rose-50/40 hover:bg-rose-50/80 border border-rose-200 rounded-md transition-all shadow-2xs group flex flex-col justify-between space-y-3"
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 bg-rose-100 text-rose-800 rounded font-mono font-bold text-[10px]">
                  DISPUTE ESCALATION
                </span>
                <span className="text-xs font-mono font-bold text-rose-700">CASE-000853</span>
              </div>
              <h4 className="text-xs font-bold text-slate-900 group-hover:text-rose-900">Chargeback Dispute Anomaly</h4>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Bank dispute adjustment recorded against payment. Routed directly to financial risk desk for operational review.
              </p>
            </div>
            <div className="flex items-center justify-between text-[11px] text-rose-700 font-medium pt-2 border-t border-rose-100">
              <span>Decision: ESCALATE (HIGH)</span>
              <span className="flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                Inspect Case →
              </span>
            </div>
          </Link>
        </div>
      </Card>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Total Cases</span>
            <Layers className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 font-mono">{summary.total_cases.toLocaleString()}</div>
          <div className="text-[11px] text-slate-400 mt-1">100% Operational Volume</div>
        </div>

        <div className="bg-white border border-emerald-100 rounded-lg p-4 shadow-xs bg-emerald-50/20">
          <div className="flex items-center justify-between text-emerald-800 text-xs font-medium">
            <span>Auto Resolved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-700 font-mono">{summary.auto_resolved.toLocaleString()}</div>
          <div className="text-[11px] text-emerald-600 font-medium mt-1">{autoResolvePercent}% Deterministic Match</div>
        </div>

        <div className="bg-white border border-sky-100 rounded-lg p-4 shadow-xs bg-sky-50/20">
          <div className="flex items-center justify-between text-sky-800 text-xs font-medium">
            <span>AI Investigation</span>
            <Bot className="w-4 h-4 text-sky-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-sky-700 font-mono">{summary.ai_investigation.toLocaleString()}</div>
          <div className="text-[11px] text-sky-600 font-medium mt-1">{aiPercent}% Evidence Verified</div>
        </div>

        <div className="bg-white border border-amber-100 rounded-lg p-4 shadow-xs bg-amber-50/20">
          <div className="flex items-center justify-between text-amber-800 text-xs font-medium">
            <span>Human Review</span>
            <UserCheck className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-700 font-mono">{summary.human_review.toLocaleString()}</div>
          <div className="text-[11px] text-amber-600 font-medium mt-1">{humanPercent}% Ops Desk Queue</div>
        </div>

        <div className="bg-white border border-rose-100 rounded-lg p-4 shadow-xs bg-rose-50/20 col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-rose-800 text-xs font-medium">
            <span>Escalated</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-700 font-mono">{summary.escalated.toLocaleString()}</div>
          <div className="text-[11px] text-rose-600 font-medium mt-1">{escalatePercent}% High-Risk Exceptions</div>
        </div>
      </div>

      {/* Financial Overview & Policy Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Financial Exposure Card */}
        <Card
          title="Financial Exposure Summary"
          subtitle="Monetary impact of open exceptions grouped by policy decision and risk level"
          className="lg:col-span-2"
        >
          <div className="space-y-5">
            <div className="bg-slate-50 border border-slate-200 rounded-md p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-xs text-slate-500 font-medium">Total Exception Financial Exposure</span>
                <div className="text-2xl font-bold text-slate-900 font-mono mt-0.5">
                  <FormatMoney amount={summary.total_financial_exposure} />
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-rose-600 font-medium flex items-center gap-1 sm:justify-end">
                  <ShieldAlert className="w-3.5 h-3.5" /> High Priority Exposure
                </span>
                <div className="text-sm font-bold text-rose-700 font-mono mt-0.5">
                  {formatINR(summary.financial_impact_by_priority["HIGH"] || 0)}
                </div>
              </div>
            </div>

            {/* Breakdown Table */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-white border border-slate-200 rounded-md">
                <div className="text-[11px] text-slate-500 font-medium">Auto-Resolve</div>
                <div className="text-sm font-semibold text-slate-800 font-mono mt-1">
                  {formatINR(summary.financial_impact_by_decision["AUTO_RESOLVE"] || 0)}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">780 cases</div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded-md">
                <div className="text-[11px] text-slate-500 font-medium">AI Investigation</div>
                <div className="text-sm font-semibold text-sky-700 font-mono mt-1">
                  {formatINR(summary.financial_impact_by_decision["AI_INVESTIGATION"] || 0)}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">50 cases</div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded-md">
                <div className="text-[11px] text-slate-500 font-medium">Human Review</div>
                <div className="text-sm font-semibold text-amber-700 font-mono mt-1">
                  {formatINR(summary.financial_impact_by_decision["HUMAN_REVIEW"] || 0)}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">40 cases</div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded-md">
                <div className="text-[11px] text-slate-500 font-medium">Escalated</div>
                <div className="text-sm font-semibold text-rose-700 font-mono mt-1">
                  {formatINR(summary.financial_impact_by_decision["ESCALATE"] || 0)}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">130 cases</div>
              </div>
            </div>
          </div>
        </Card>

        {/* Engine Match Classification */}
        <Card
          title="Engine Reconciliation Breakdown"
          subtitle="Deterministic match classifications from Day 3 pipeline"
        >
          <div className="space-y-3.5">
            <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-600 font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Matched Transactions
              </span>
              <span className="font-bold text-slate-900 font-mono">{summary.matched_cases}</span>
            </div>

            <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-600 font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500"></span> Ambiguous Retries / Candidates
              </span>
              <span className="font-bold text-slate-900 font-mono">{summary.ambiguous_cases}</span>
            </div>

            <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-600 font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span> Unmatched Records
              </span>
              <span className="font-bold text-slate-900 font-mono">{summary.unmatched_cases}</span>
            </div>

            <div className="flex items-center justify-between text-xs pb-2">
              <span className="text-slate-600 font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span> Discrepancies & Variances
              </span>
              <span className="font-bold text-slate-900 font-mono">{summary.discrepancy_cases}</span>
            </div>

            {/* Proportion Bar */}
            <div className="pt-2">
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden flex">
                <div style={{ width: `${(summary.matched_cases / summary.total_cases) * 100}%` }} className="bg-emerald-500" title="Matched" />
                <div style={{ width: `${(summary.ambiguous_cases / summary.total_cases) * 100}%` }} className="bg-indigo-500" title="Ambiguous" />
                <div style={{ width: `${(summary.unmatched_cases / summary.total_cases) * 100}%` }} className="bg-amber-500" title="Unmatched" />
                <div style={{ width: `${(summary.discrepancy_cases / summary.total_cases) * 100}%` }} className="bg-rose-500" title="Discrepancy" />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* High Priority Cases Table */}
      <Card
        title="High Priority Operational Exceptions"
        subtitle="Exceptions requiring immediate operations desk review or escalation"
        headerAction={
          <Link
            to="/cases?priority=HIGH"
            className="text-xs text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1"
          >
            View all 170 High Priority Cases <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 font-medium">
                <th className="py-2.5 px-3">Case ID</th>
                <th className="py-2.5 px-3">Order ID</th>
                <th className="py-2.5 px-3">Exception Category</th>
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3">Policy Decision</th>
                <th className="py-2.5 px-3 text-right">Financial Impact</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {recentCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 px-3 font-mono font-medium text-sky-600">
                    <Link to={`/cases/${c.case_id}`} className="hover:underline">
                      {c.case_id}
                    </Link>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-slate-600">{c.order_id}</td>
                  <td className="py-2.5 px-3 font-medium text-slate-700">{c.exception_type.replace(/_/g, " ")}</td>
                  <td className="py-2.5 px-3">
                    <PriorityBadge priority={c.priority} />
                  </td>
                  <td className="py-2.5 px-3">
                    <DecisionBadge decision={c.decision} />
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-900">
                    <FormatMoney amount={c.financial_impact} />
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <Link
                      to={`/cases/${c.case_id}`}
                      className="text-xs text-sky-600 hover:text-sky-800 font-medium"
                    >
                      Inspect →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
