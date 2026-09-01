/**
 * TypeScript API interfaces matching ReconGuard FastAPI schemas.
 */

export interface DashboardSummary {
  total_cases: number;
  auto_resolved: number;
  ai_investigation: number;
  human_review: number;
  escalated: number;
  total_financial_exposure: number;
  high_priority_cases: number;
  medium_priority_cases: number;
  low_priority_cases: number;
  matched_cases: number;
  unmatched_cases: number;
  discrepancy_cases: number;
  ambiguous_cases: number;
  financial_impact_by_decision: Record<string, number>;
  financial_impact_by_priority: Record<string, number>;
  exception_type_counts: Record<string, number>;
}

export interface CaseSummary {
  case_id: string;
  order_id: string;
  decision: "AUTO_RESOLVE" | "AI_INVESTIGATION" | "HUMAN_REVIEW" | "ESCALATE";
  exception_type: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  financial_impact: number;
  match_method: string;
  match_confidence: number;
  payment_ids: string[];
  settlement_ids: string[];
  invoice_id: string | null;
  adjustment_ids: string[];
  requires_ai: boolean;
  requires_human: boolean;
  created_at: string;
}

export interface CaseListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  cases: CaseSummary[];
}

export interface TransactionChainOrder {
  order_id: string;
  customer_id?: string | null;
  amount: number;
  currency: string;
  status?: string | null;
  created_at?: string | null;
}

export interface TransactionChainPayment {
  payment_id: string;
  order_id?: string | null;
  amount: number;
  currency: string;
  status?: string | null;
  payment_method?: string | null;
  utr?: string | null;
  created_at?: string | null;
}

export interface TransactionChainSettlement {
  settlement_id: string;
  payment_id?: string | null;
  amount: number;
  fee: number;
  tax: number;
  net_amount: number;
  utr?: string | null;
  status?: string | null;
  settled_at?: string | null;
}

export interface TransactionChainInvoice {
  invoice_id: string;
  order_id: string;
  amount: number;
  tax_amount: number;
  status?: string | null;
  created_at?: string | null;
}

export interface TransactionChainAdjustment {
  adjustment_id: string;
  type?: string | null;
  amount: number;
  related_id?: string | null;
  reason?: string | null;
  created_at?: string | null;
}

export interface TransactionChain {
  case_id: string;
  order_id: string;
  order?: TransactionChainOrder | null;
  payments: TransactionChainPayment[];
  settlements: TransactionChainSettlement[];
  invoice?: TransactionChainInvoice | null;
  adjustments: TransactionChainAdjustment[];
}

export interface CaseDetail extends CaseSummary {
  reason: string;
  explanation: string;
  next_action: string;
  transaction_chain?: TransactionChain | null;
}

export interface EvidenceResponse {
  case_id: string;
  order_id: string;
  match_method: string;
  match_confidence: number;
  evidence: Record<string, unknown>;
  reason: string;
  explanation: string;
  match_status: string;
  match_discrepancy_reason: string;
}

export interface ToolCallRecord {
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  timestamp: string;
}

export interface InvestigationResponse {
  case_id: string;
  order_id: string;
  finding: string;
  root_cause: string;
  evidence: Record<string, unknown>;
  confidence: number;
  recommendation: string;
  requires_human_review: boolean;
  supporting_payment_ids: string[];
  supporting_settlement_ids: string[];
  supporting_invoice_id: string | null;
  investigation_status: "COMPLETED" | "INCONCLUSIVE" | "FAILED";
  tool_trace: ToolCallRecord[];
  provider_used: string;
  created_at: string;
}

export interface InvestigationListResponse {
  total: number;
  investigations: InvestigationResponse[];
}

