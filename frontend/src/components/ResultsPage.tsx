import { downloadReportUrl, type AnalysisResponse, type NdviResponse, type TimeseriesResponse } from "../api";
import TimeSeriesChart from "./TimeSeriesChart";

type PixelSample = {
  lat: number;
  lng: number;
  ndvi: number | null;
  vegetation_status: string;
  class_color: string;
} | null;

function asNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export default function ResultsPage({
  dark,
  ndvi,
  analysis,
  ts,
  lastPixel,
  onBack,
}: {
  dark: boolean;
  ndvi: NdviResponse | null;
  analysis: AnalysisResponse | null;
  ts: TimeseriesResponse | null;
  lastPixel: PixelSample;
  onBack: () => void;
}) {
  const ndviStats = ndvi?.ndvi_stats ?? {};
  const health = analysis?.health_distribution ?? {};
  const healthyPct = asNumber(ndviStats.healthy_pct) ?? asNumber(health.healthy_pct) ?? 0;
  const stressedPct = asNumber(ndviStats.stressed_pct) ?? asNumber(health.stressed_pct) ?? 0;
  const moderatePct = asNumber(ndviStats.moderate_pct) ?? asNumber(health.moderate_pct) ?? 0;
  const barePct = asNumber(ndviStats.bare_water_pct) ?? asNumber(health.bare_water_pct) ?? 0;

  const anomaly = analysis?.anomaly_detection ?? {};
  const perf = analysis?.model_performance ?? {};
  const rfAccuracyPct = asNumber(perf.rf_accuracy_pct);
  const rfKappa = asNumber(perf.rf_kappa);
  const fertilizer = analysis?.fertilizer_recommendation ?? {};
  const irrigation = analysis?.irrigation_plan ?? {};

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Results page</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Zonal analysis, AI anomalies, and automated agronomic decisions
            </p>
          </div>
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Back to map
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/40">
          <div className="text-xs uppercase text-emerald-700 dark:text-emerald-300">Healthy area</div>
          <div className="mt-1 text-2xl font-semibold">{healthyPct.toFixed(1)}%</div>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40">
          <div className="text-xs uppercase text-amber-700 dark:text-amber-300">Stressed area</div>
          <div className="mt-1 text-2xl font-semibold">{stressedPct.toFixed(1)}%</div>
        </div>
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 dark:border-sky-900 dark:bg-sky-950/40">
          <div className="text-xs uppercase text-sky-700 dark:text-sky-300">Moderate area</div>
          <div className="mt-1 text-2xl font-semibold">{moderatePct.toFixed(1)}%</div>
        </div>
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/40">
          <div className="text-xs uppercase text-rose-700 dark:text-rose-300">Bare/water area</div>
          <div className="mt-1 text-2xl font-semibold">{barePct.toFixed(1)}%</div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-2 text-sm font-semibold">System performance</h3>
        <div className="text-sm text-slate-600 dark:text-slate-300">
          <div>RF accuracy: {rfAccuracyPct != null ? `${rfAccuracyPct.toFixed(1)}%` : "-"}</div>
          <div>RF kappa: {rfKappa != null ? rfKappa.toFixed(3) : "-"}</div>
          <div>Trees: {asNumber(perf.rf_trees) ?? "-"}</div>
          <div>Evaluation: {String(perf.evaluation ?? "-")}</div>
        </div>
        <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{String(perf.note ?? "")}</div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">Field zones</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500">
                <tr>
                  <th className="pb-2">Zone</th>
                  <th className="pb-2">Mean NDVI</th>
                  <th className="pb-2">Min</th>
                  <th className="pb-2">Max</th>
                  <th className="pb-2">Std</th>
                </tr>
              </thead>
              <tbody>
                {(analysis?.zones ?? []).map((z, i) => (
                  <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2">{String(z.zone_name ?? `Field ${i + 1}`)}</td>
                    <td className="py-2">{asNumber(z.mean_ndvi)?.toFixed(3) ?? "-"}</td>
                    <td className="py-2">{asNumber(z.min_ndvi)?.toFixed(3) ?? "-"}</td>
                    <td className="py-2">{asNumber(z.max_ndvi)?.toFixed(3) ?? "-"}</td>
                    <td className="py-2">{asNumber(z.std_ndvi)?.toFixed(3) ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">AI anomaly detection</h3>
          <div className="text-sm text-slate-600 dark:text-slate-300">
            <div>Model: {String(anomaly.model ?? "-")}</div>
            <div>Status: {String(anomaly.status ?? "-")}</div>
            <div>Severity: {String(anomaly.severity ?? "-")}</div>
            <div>Anomaly ratio: {asNumber(anomaly.anomaly_ratio_pct)?.toFixed(1) ?? "0.0"}%</div>
            <div>Sample size: {asNumber(anomaly.sample_size) ?? "-"}</div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">Fertilizer recommendation</h3>
          <div className="text-sm text-slate-700 dark:text-slate-200">
            <div className="font-medium">Priority: {String(fertilizer.priority ?? "-")}</div>
            <div className="mt-1 text-slate-600 dark:text-slate-300">{String(fertilizer.rate_hint ?? "-")}</div>
          </div>
          <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Exact fertilizer names
          </div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {(Array.isArray(fertilizer.recommended_products) ? fertilizer.recommended_products : []).map((p, i) => (
              <li key={`fert-prod-${i}`}>{String(p)}</li>
            ))}
          </ul>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            {(Array.isArray(fertilizer.actions) ? fertilizer.actions : []).map((a, i) => (
              <li key={i}>{String(a)}</li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">Irrigation planning</h3>
          <div className="text-sm text-slate-700 dark:text-slate-200">
            <div className="font-medium">Strategy: {String(irrigation.strategy ?? "-")}</div>
            <div className="mt-1 text-slate-600 dark:text-slate-300">{String(irrigation.frequency_hint ?? "-")}</div>
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">
            {(Array.isArray(irrigation.actions) ? irrigation.actions : []).map((a, i) => (
              <li key={i}>{String(a)}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">Pixel detail</h3>
          {lastPixel ? (
            <div className="text-sm text-slate-700 dark:text-slate-200">
              <div>
                Point: {lastPixel.lat.toFixed(5)}, {lastPixel.lng.toFixed(5)}
              </div>
              <div>NDVI: {lastPixel.ndvi != null ? lastPixel.ndvi.toFixed(3) : "-"}</div>
              <div style={{ color: lastPixel.class_color }}>Status: {lastPixel.vegetation_status}</div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">Click the map after running analysis to inspect a pixel.</div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-2 text-sm font-semibold">Exports</h3>
          {ndvi?.run_id ? (
            <div className="flex flex-col gap-2 text-sm">
              <a className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-700" href={downloadReportUrl(ndvi.run_id, "pdf")}>Download PDF</a>
              <a className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-700" href={downloadReportUrl(ndvi.run_id, "csv")}>Download CSV</a>
              <a className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-700" href={downloadReportUrl(ndvi.run_id, "geotiff")}>GeoTIFF</a>
            </div>
          ) : (
            <div className="text-sm text-slate-500">Run analysis to enable report downloads.</div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold">NDVI time series</h3>
          {ts?.change_summary && Object.keys(ts.change_summary).length > 0 ? (
            <span className="text-xs text-slate-500">
              Trend: {String((ts.change_summary as { trend?: string }).trend ?? "-")}
            </span>
          ) : null}
        </div>
        <TimeSeriesChart data={ts?.series ?? []} dark={dark} />
      </div>
    </div>
  );
}
