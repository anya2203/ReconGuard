import type {
  BenchmarkMetrics,
  CaseAuditTrail,
  CaseDetail,
  CaseListResponse,
  DashboardSummary,
  EvidenceResponse,
  InvestigationListResponse,
  InvestigationResponse,
} from "../types/api";

const BASE_URL = "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let errorDetail = `Request failed with status ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = errorJson.detail;
        }
      } catch {
        // Use default message
      }
      throw new ApiError(errorDetail, res.status);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : "Network error";
    throw new ApiError(message, 0);
  }
}

export const api = {
  getHealth: () => request<{ status: string; service?: string }>("/health"),

  getDashboardSummary: () => request<DashboardSummary>("/api/dashboard/summary"),

  getCases: (params?: {
    page?: number;
    page_size?: number;
    decision?: string;
    priority?: string;
    exception_type?: string;
    search?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    if (params?.decision && params.decision !== "ALL") query.set("decision", params.decision);
    if (params?.priority && params.priority !== "ALL") query.set("priority", params.priority);
    if (params?.exception_type && params.exception_type !== "ALL")
      query.set("exception_type", params.exception_type);
    if (params?.search && params.search.trim()) query.set("search", params.search.trim());

    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<CaseListResponse>(`/api/cases${qs}`);
  },

  getCaseDetail: (caseId: string) => request<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`),

  getCaseEvidence: (caseId: string) =>
    request<EvidenceResponse>(`/api/cases/${encodeURIComponent(caseId)}/evidence`),

  getInvestigations: () => request<InvestigationListResponse>("/api/investigations"),

  getInvestigation: (caseId: string) =>
    request<InvestigationResponse>(`/api/investigations/${encodeURIComponent(caseId)}`),

  investigateCase: (caseId: string, provider: string = "mock") =>
    request<InvestigationResponse>(`/api/cases/${encodeURIComponent(caseId)}/investigate`, {
      method: "POST",
      body: JSON.stringify({ provider }),
    }),

  getAuditTrail: (caseId: string) =>
    request<CaseAuditTrail>(`/api/audit/${encodeURIComponent(caseId)}`),

  getBenchmarkMetrics: () =>
    request<BenchmarkMetrics>("/api/dashboard/benchmark"),
};

