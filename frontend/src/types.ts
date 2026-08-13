export type Trace = {
  agent: string;
  duration_ms: number;
  tools_used: string[];
  docs_retrieved: string[];
  recommendation?: string | null;
  confidence?: number | null;
  status: string;
};

export type Decision = {
  service: string;
  observed_metrics: Record<string, unknown>;
  evidence: string[];
  recommendation: string;
  reason: string;
  confidence: number;
};

export type Incident = {
  id: string;
  prompt: string;
  scenario_id: string;
  service: string;
  status: string;
  decision: Decision;
  verification: Record<string, unknown>;
  traces: Trace[];
  release?: Record<string, unknown>;
  logs?: string[];
};

export type OpsTraces = {
  incident_id: string;
  traces: Trace[];
  runtime_ms?: number;
  recommendation?: string;
  confidence?: number;
  status?: string;
  docs_retrieved?: string[];
  tools_used?: string[];
  service?: string;
  decision?: Decision;
  verification?: Record<string, unknown>;
};

export type ApiErrorBody = {
  error?: string;
  code?: string;
  detail?: string;
  message?: string;
};
