export interface AdviceMetric {
  name: string;
  value: number;
  unit?: string | null;
  dateISO: string;
}

export interface AdviceResponseModel {
  answer: string;
  usedMetrics: AdviceMetric[];
  disclaimer: boolean;
}
