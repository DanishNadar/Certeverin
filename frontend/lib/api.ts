export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type SkillStat = {
  skill: string;
  category: string;
  job_count: number;
  job_frequency: number;
  required_mentions: number;
  preferred_mentions: number;
  confidence: number;
  snippets: string[];
};

export type CertRecommendation = {
  certification_name: string;
  provider: string;
  official_url: string;
  status: string;
  cost: number | null;
  difficulty: string;
  score: number;
  covered_skills: string[];
  missing_top_skills: string[];
  notes: string;
};

export type SearchRun = {
  id: number;
  target_title: string;
  location: string;
  seniority: string;
  limit: number;
  sources: string[];
  status: string;
  summary: {
    jobs_analyzed?: number;
    top_skills?: SkillStat[];
    top_certifications?: CertRecommendation[];
    recommendation?: string;
    recommendations?: string[];
    demo_labeled?: boolean;
    demo_reason?: string | null;
    collection_warning?: string | null;
    source_limits?: Record<string, number>;
  };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {"Content-Type": "application/json", ...(init?.headers ?? {})}
    });
  } catch {
    throw new Error("Cannot reach the backend API. Start it with `uvicorn app.main:app` from the backend folder, then try again.");
  }
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createRun(payload: Record<string, unknown>) {
  return request<SearchRun>("/api/search-runs", {method: "POST", body: JSON.stringify(payload)});
}

export function getSkills(runId: number) {
  return request<SkillStat[]>(`/api/search-runs/${runId}/skills`);
}

export function getCertifications(runId: number) {
  return request<CertRecommendation[]>(`/api/search-runs/${runId}/certifications`);
}

export function generateReport(runId: number) {
  return request<{report_id: number; download_url: string; file_path: string}>(`/api/search-runs/${runId}/generate-report`, {method: "POST"});
}
