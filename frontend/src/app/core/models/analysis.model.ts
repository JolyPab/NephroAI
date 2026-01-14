export interface MetricBrief {
  name: string;
  value?: number | null;
  value_text?: string | null;
  unit?: string | null;
  ref_min?: number | null;
  ref_max?: number | null;
}

export interface AnalysisSummary {
  id: string;
  date?: string | null;
  taken_at?: string | null;
  created_at?: string | null;
  source_pdf: string;
  metrics_count: number;
  metrics: MetricBrief[];
}

export interface MetricSeriesPoint {
  t: string;
  y: number;
  refMin?: number | null;
  refMax?: number | null;
  unit?: string | null;
  stage?: string | null;
  stage_label?: string | null;
}

export interface CategoricalSeriesPoint {
  date: string;
  value_text: string;
}

export interface MetricSeriesResponse {
  series_type: 'numeric' | 'categorical';
  points: MetricSeriesPoint[] | CategoricalSeriesPoint[];
  stage?: string | null;
  stage_label?: string | null;
}
