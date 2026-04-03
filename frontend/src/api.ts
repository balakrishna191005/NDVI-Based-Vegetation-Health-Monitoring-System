const base = "";

export type Satellite = "sentinel2" | "landsat89";

export interface NdviRequestBody {
  roi: Record<string, unknown>;
  start_date: string;
  end_date: string;
  satellite: Satellite;
  max_cloud_pct?: number;
}

export interface NdviResponse {
  success: boolean;
  message?: string | null;
  map_id?: string | null;
  map_token?: string | null;
  tile_fetcher?: string | null;
  classification_map_id?: string | null;
  classification_token?: string | null;
  classification_tile_url?: string | null;
  ndvi_stats: Record<string, number | null | undefined>;
  legend: Array<Record<string, unknown>>;
  bounds?: number[] | null;
  run_id?: string | null;
}

export async function postGetNdvi(body: NdviRequestBody): Promise<NdviResponse> {
  const r = await fetch(`${base}/get-ndvi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}

export async function postGetNdviLatest(body: NdviRequestBody): Promise<NdviResponse> {
  const r = await fetch(`${base}/get-ndvi/latest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}

export interface TimeseriesResponse {
  series: Array<{
    date: string;
    mean_ndvi?: number | null;
    median_ndvi?: number | null;
    note?: string | null;
  }>;
  change_summary: Record<string, unknown>;
  anomalies: Array<Record<string, unknown>>;
}

export async function postGetTimeseries(body: NdviRequestBody): Promise<TimeseriesResponse> {
  const r = await fetch(`${base}/get-timeseries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}

export interface AnalysisResponse {
  zonal: Record<string, unknown>;
  zones?: Array<Record<string, unknown>>;
  health_distribution?: Record<string, unknown>;
  anomaly_detection?: Record<string, unknown>;
  model_performance?: Record<string, unknown>;
  rf_map_id?: string | null;
  rf_token?: string | null;
  rf_tile_url?: string | null;
  rf_legend: Array<Record<string, unknown>>;
  kmeans_map_id?: string | null;
  kmeans_token?: string | null;
  kmeans_tile_url?: string | null;
  fertilizer_recommendation?: Record<string, unknown>;
  irrigation_plan?: Record<string, unknown>;
}

export async function postGetAnalysis(
  body: NdviRequestBody & { include_kmeans?: boolean; rf_trees?: number }
): Promise<AnalysisResponse> {
  const r = await fetch(`${base}/get-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}

export async function sampleNdviPoint(body: {
  roi: Record<string, unknown>;
  lat: number;
  lon: number;
  start_date: string;
  end_date: string;
  satellite: Satellite;
  max_cloud_pct?: number;
}) {
  const r = await fetch(`${base}/sample-ndvi-point`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json() as Promise<{
    ndvi: number | null;
    vegetation_status: string;
    class_color: string;
  }>;
}

export function downloadReportUrl(runId: string, format: "pdf" | "csv" | "geotiff") {
  const q = new URLSearchParams({ run_id: runId, format });
  return `${base}/download-report?${q.toString()}`;
}
