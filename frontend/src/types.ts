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
};
