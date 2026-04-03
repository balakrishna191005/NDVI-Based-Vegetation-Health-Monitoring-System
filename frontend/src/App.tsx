import { useCallback, useEffect, useMemo, useState } from "react";
import L from "leaflet";
import toast from "react-hot-toast";
import {
  downloadReportUrl,
  postGetAnalysis,
  postGetNdvi,
  postGetNdviLatest,
  postGetTimeseries,
  sampleNdviPoint,
  type AnalysisResponse,
  type NdviResponse,
  type Satellite,
  type TimeseriesResponse,
} from "./api";
import NDVIMap from "./components/NDVIMap";
import type { MapStyle } from "./components/NDVIMap";
import ResultsPage from "./components/ResultsPage";
import ThemeToggle from "./components/ThemeToggle";
import TimeSeriesChart from "./components/TimeSeriesChart";

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    return document.documentElement.classList.contains("dark");
  });
  useEffect(() => {
    const v = localStorage.getItem("ndvi-theme");
    if (v === "dark") {
      document.documentElement.classList.add("dark");
      setDark(true);
    } else if (v === "light") {
      document.documentElement.classList.remove("dark");
      setDark(false);
    }
  }, []);
  const toggle = () => {
    setDark((d) => {
      const next = !d;
      if (next) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("ndvi-theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("ndvi-theme", "light");
      }
      return next;
    });
  };
  return { dark, toggle };
}

export default function App() {
  const { dark, toggle } = useDarkMode();
  const [roi, setRoi] = useState<Record<string, unknown> | null>(null);
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2024-03-01");
  const [compareStart, setCompareStart] = useState("2023-01-01");
  const [compareEnd, setCompareEnd] = useState("2023-03-01");
  const [satellite, setSatellite] = useState<Satellite>("sentinel2");
  const [cloud, setCloud] = useState(20);
  const [loading, setLoading] = useState(false);
  const [ndvi, setNdvi] = useState<NdviResponse | null>(null);
  const [compareNdvi, setCompareNdvi] = useState<NdviResponse | null>(null);
  const [compareOpacity, setCompareOpacity] = useState(0.5);
  const [ts, setTs] = useState<TimeseriesResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [showClass, setShowClass] = useState(true);
  const [showRf, setShowRf] = useState(false);
  const [showKm, setShowKm] = useState(false);
  const [mapStyle, setMapStyle] = useState<MapStyle>("light");
  const [locationQuery, setLocationQuery] = useState("");
  const [searchLat, setSearchLat] = useState("");
  const [searchLng, setSearchLng] = useState("");
  const [activePlaceName, setActivePlaceName] = useState<string | null>(null);
  const [mapTarget, setMapTarget] = useState<{ lat: number; lng: number; zoom?: number } | null>(null);
  const [showResultsPage, setShowResultsPage] = useState(false);
  const [lastPixelSample, setLastPixelSample] = useState<{
    lat: number;
    lng: number;
    ndvi: number | null;
    vegetation_status: string;
    class_color: string;
  } | null>(null);

  const bodyBase = useMemo(
    () => ({
      roi: roi ?? { type: "Polygon", coordinates: [] },
      start_date: start,
      end_date: end,
      satellite,
      max_cloud_pct: cloud,
    }),
    [roi, start, end, satellite, cloud]
  );

  const onDrawPolygon = useCallback((gj: Record<string, unknown>) => {
    setRoi(gj);
    toast.success("ROI updated — draw finished");
  }, []);

  const reverseGeocode = useCallback(async (lat: number, lng: number) => {
    const u = new URL("https://nominatim.openstreetmap.org/reverse");
    u.searchParams.set("format", "jsonv2");
    u.searchParams.set("lat", String(lat));
    u.searchParams.set("lon", String(lng));
    const res = await fetch(u.toString(), {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error("Could not resolve area name for this point.");
    const data = (await res.json()) as { display_name?: string };
    return data.display_name ?? `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  }, []);

  const searchByPlace = useCallback(async () => {
    const q = locationQuery.trim();
    if (!q) {
      toast.error("Enter an area name to search.");
      return;
    }
    try {
      const u = new URL("https://nominatim.openstreetmap.org/search");
      u.searchParams.set("q", q);
      u.searchParams.set("format", "jsonv2");
      u.searchParams.set("limit", "1");
      const res = await fetch(u.toString(), {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) throw new Error("Location search failed.");
      const rows = (await res.json()) as Array<{ lat: string; lon: string; display_name?: string }>;
      if (!rows.length) {
        toast.error("No matching area found.");
        return;
      }
      const first = rows[0];
      const lat = Number(first.lat);
      const lng = Number(first.lon);
      setMapTarget({ lat, lng, zoom: 12 });
      setSearchLat(lat.toFixed(6));
      setSearchLng(lng.toFixed(6));
      setActivePlaceName(first.display_name ?? q);
      toast.success("Moved map to selected area.");
    } catch (e) {
      toast.error(String(e));
    }
  }, [locationQuery]);

  const searchByCoordinates = useCallback(async () => {
    const lat = Number(searchLat);
    const lng = Number(searchLng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      toast.error("Enter valid latitude and longitude values.");
      return;
    }
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      toast.error("Latitude must be -90..90 and longitude -180..180.");
      return;
    }
    try {
      setMapTarget({ lat, lng, zoom: 12 });
      const label = await reverseGeocode(lat, lng);
      setActivePlaceName(label);
      toast.success("Moved map to coordinates.");
    } catch (e) {
      toast.error(String(e));
      setActivePlaceName(`${lat.toFixed(5)}, ${lng.toFixed(5)}`);
    }
  }, [searchLat, searchLng, reverseGeocode]);

  const handleMapLocationPick = useCallback(
    async (lat: number, lng: number) => {
      setSearchLat(lat.toFixed(6));
      setSearchLng(lng.toFixed(6));
      try {
        const label = await reverseGeocode(lat, lng);
        setActivePlaceName(label);
      } catch {
        setActivePlaceName(`${lat.toFixed(5)}, ${lng.toFixed(5)}`);
      }
    },
    [reverseGeocode]
  );

  const runPipeline = useCallback(async () => {
    if (!roi) {
      toast.error("Draw a polygon on the map first.");
      return;
    }
    setLoading(true);
    try {
      const [n, t, a] = await Promise.all([
        postGetNdvi(bodyBase),
        postGetTimeseries(bodyBase),
        postGetAnalysis({ ...bodyBase, include_kmeans: true, rf_trees: 60 }),
      ]);
      setNdvi(n);
      setTs(t);
      setAnalysis(a);
      setShowResultsPage(true);
      if (n.message) toast(n.message, { icon: "⚠️" });
      else toast.success("Analysis complete");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setLoading(false);
    }
  }, [bodyBase, roi]);

  const runLatest = useCallback(async () => {
    if (!roi) {
      toast.error("Draw a polygon on the map first.");
      return;
    }
    setLoading(true);
    try {
      const n = await postGetNdviLatest(bodyBase);
      setNdvi(n);
      toast.success("Latest clear composite loaded");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setLoading(false);
    }
  }, [bodyBase, roi]);

  const runCompare = useCallback(async () => {
    if (!roi) {
      toast.error("Draw a polygon on the map first.");
      return;
    }
    setLoading(true);
    try {
      const c = await postGetNdvi({
        roi,
        start_date: compareStart,
        end_date: compareEnd,
        satellite,
        max_cloud_pct: cloud,
      });
      setCompareNdvi(c);
      toast.success("Comparison period loaded");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setLoading(false);
    }
  }, [roi, compareStart, compareEnd, satellite, cloud]);

  const handleMapClick = useCallback(
    async (lat: number, lng: number, map: L.Map) => {
      if (!roi || !ndvi?.tile_fetcher) {
        toast.error("Run analysis first to enable NDVI sampling.");
        return;
      }
      const p = L.popup({ maxWidth: 280, className: "ndvi-popup" })
        .setLatLng([lat, lng])
        .setContent("<div class='text-sm'>Sampling…</div>")
        .openOn(map);
      try {
        const r = await sampleNdviPoint({
          roi,
          lat,
          lon: lng,
          start_date: start,
          end_date: end,
          satellite,
          max_cloud_pct: cloud,
        });
        p.setContent(
          `<div class="text-sm space-y-1 p-1"><div class="font-semibold">NDVI: ${
            r.ndvi != null ? r.ndvi.toFixed(3) : "—"
          }</div><div style="color:${r.class_color}">${r.vegetation_status}</div></div>`
        );
        setLastPixelSample({
          lat,
          lng,
          ndvi: r.ndvi,
          vegetation_status: r.vegetation_status,
          class_color: r.class_color,
        });
      } catch (e) {
        p.setContent(`<div class="text-sm text-red-600">${String(e)}</div>`);
      }
    },
    [roi, ndvi, start, end, satellite, cloud]
  );

  const mean = ndvi?.ndvi_stats?.mean as number | undefined | null;
  const alertLow = mean != null && mean < 0.3;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">NDVI Vegetation Monitor</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Automated GEE pipeline — draw ROI, pick dates, run analysis
            </p>
          </div>
          <ThemeToggle dark={dark} onToggle={toggle} />
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[380px_1fr]">
        <aside className="space-y-4">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Parameters
            </h2>
            <label className="block text-sm font-medium">Start date</label>
            <input
              type="date"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <label className="mt-3 block text-sm font-medium">End date</label>
            <input
              type="date"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
            <label className="mt-3 block text-sm font-medium">Satellite</label>
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              value={satellite}
              onChange={(e) => setSatellite(e.target.value as Satellite)}
            >
              <option value="sentinel2">Sentinel-2 (MSI)</option>
              <option value="landsat89">Landsat 8/9</option>
            </select>
            <label className="mt-3 block text-sm font-medium">Max cloud %</label>
            <input
              type="number"
              min={0}
              max={100}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              value={cloud}
              onChange={(e) => setCloud(Number(e.target.value))}
            />
            <label className="mt-3 block text-sm font-medium">Base map</label>
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              value={mapStyle}
              onChange={(e) => setMapStyle(e.target.value as MapStyle)}
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="satellite">Satellite</option>
            </select>
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                disabled={loading}
                onClick={runPipeline}
                className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow transition hover:bg-emerald-500 disabled:opacity-60"
              >
                {loading ? "Running…" : "Run analysis"}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={runLatest}
                className="inline-flex items-center justify-center rounded-xl border border-emerald-600 px-4 py-2.5 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
              >
                Real-time NDVI (latest clear)
              </button>
              <button
                type="button"
                disabled={!analysis}
                onClick={() => setShowResultsPage(true)}
                className="inline-flex items-center justify-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Open results page
              </button>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Multi-date comparison
            </h2>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-500">Compare start</label>
                <input
                  type="date"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  value={compareStart}
                  onChange={(e) => setCompareStart(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Compare end</label>
                <input
                  type="date"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  value={compareEnd}
                  onChange={(e) => setCompareEnd(e.target.value)}
                />
              </div>
            </div>
            <button
              type="button"
              disabled={loading}
              onClick={runCompare}
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Load comparison layer
            </button>
            <label className="mt-3 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
              <span>Blend</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={compareOpacity}
                onChange={(e) => setCompareOpacity(Number(e.target.value))}
              />
              <span>{Math.round(compareOpacity * 100)}%</span>
            </label>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Map overlays
            </h2>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={showClass} onChange={(e) => setShowClass(e.target.checked)} />
              Classification colors
            </label>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={showRf} onChange={(e) => setShowRf(e.target.checked)} />
              Random Forest layer
            </label>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={showKm} onChange={(e) => setShowKm(e.target.checked)} />
              KMeans clusters
            </label>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Area search
            </h2>
            <label className="block text-sm font-medium">Search by place name</label>
            <div className="mt-1 flex gap-2">
              <input
                type="text"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
                placeholder="e.g. Pune, Maharashtra"
                value={locationQuery}
                onChange={(e) => setLocationQuery(e.target.value)}
              />
              <button
                type="button"
                onClick={searchByPlace}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                Search
              </button>
            </div>

            <label className="mt-3 block text-sm font-medium">Search by coordinates</label>
            <div className="mt-1 grid grid-cols-2 gap-2">
              <input
                type="number"
                step="any"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
                placeholder="Latitude"
                value={searchLat}
                onChange={(e) => setSearchLat(e.target.value)}
              />
              <input
                type="number"
                step="any"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
                placeholder="Longitude"
                value={searchLng}
                onChange={(e) => setSearchLng(e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={searchByCoordinates}
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Go to coordinates
            </button>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {activePlaceName ? `Current area: ${activePlaceName}` : "Current area: —"}
            </div>
            <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Tip: click any map point to auto-fill coordinates.
            </div>
          </section>

          {ndvi?.run_id ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Exports
              </h2>
              <div className="flex flex-col gap-2">
                <a
                  className="rounded-lg bg-slate-900 px-3 py-2 text-center text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                  href={downloadReportUrl(ndvi.run_id!, "pdf")}
                >
                  Download PDF
                </a>
                <a
                  className="rounded-lg border border-slate-300 px-3 py-2 text-center text-sm dark:border-slate-600"
                  href={downloadReportUrl(ndvi.run_id!, "csv")}
                >
                  Download CSV
                </a>
                <a
                  className="rounded-lg border border-slate-300 px-3 py-2 text-center text-sm dark:border-slate-600"
                  href={downloadReportUrl(ndvi.run_id!, "geotiff")}
                >
                  GeoTIFF (GEE link)
                </a>
              </div>
            </section>
          ) : null}
        </aside>

        <div className="space-y-4">
          {showResultsPage ? (
            <ResultsPage
              dark={dark}
              ndvi={ndvi}
              analysis={analysis}
              ts={ts}
              lastPixel={lastPixelSample}
              onBack={() => setShowResultsPage(false)}
            />
          ) : (
            <>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs uppercase text-slate-500">Mean NDVI</div>
              <div className="mt-1 text-2xl font-semibold">
                {mean != null && mean !== undefined ? mean.toFixed(3) : "—"}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs uppercase text-slate-500">Health</div>
              <div className="mt-1 text-lg font-medium">
                {mean == null ? "—" : mean >= 0.5 ? "Healthy" : mean >= 0.3 ? "Moderate" : "Stressed"}
              </div>
            </div>
            <div
              className={`rounded-2xl border p-4 shadow-sm ${
                alertLow
                  ? "border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950/40"
                  : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              }`}
            >
              <div className="text-xs uppercase text-slate-500">Alerts</div>
              <div className="mt-1 text-sm font-medium">
                {alertLow ? "Low vegetation detected (NDVI < 0.3)" : "No critical alerts"}
              </div>
            </div>
          </div>

          <div className="h-[480px] overflow-hidden rounded-2xl border border-slate-200 shadow-md dark:border-slate-800">
            <NDVIMap
              mapStyle={mapStyle}
              roi={roi}
              bounds={ndvi?.bounds ?? undefined}
              ndviTileUrl={ndvi?.tile_fetcher}
              classTileUrl={ndvi?.classification_tile_url}
              rfTileUrl={analysis?.rf_tile_url}
              kmeansTileUrl={analysis?.kmeans_tile_url}
              showClassification={showClass}
              showRf={showRf}
              showKmeans={showKm}
              compareNdviUrl={compareNdvi?.tile_fetcher}
              compareOpacity={compareOpacity}
              mapTarget={mapTarget}
              onDrawPolygon={onDrawPolygon}
              onMapClick={handleMapClick}
              onPickLocation={handleMapLocationPick}
              clickSampleEnabled={Boolean(ndvi?.tile_fetcher)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <h3 className="mb-2 text-sm font-semibold">NDVI legend</h3>
              <ul className="space-y-1 text-sm">
                {(ndvi?.legend ?? []).map((row) => (
                  <li key={String(row.class_id)} className="flex items-center gap-2">
                    <span
                      className="h-3 w-6 rounded"
                      style={{ backgroundColor: String(row.color ?? "#ccc") }}
                    />
                    <span>
                      {String(row.label)} ({Number(row.ndvi_min).toFixed(1)} – {Number(row.ndvi_max).toFixed(1)})
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold">NDVI time series</h3>
              {ts?.change_summary && Object.keys(ts.change_summary).length > 0 ? (
                <span className="text-xs text-slate-500">
                  Trend: {String((ts.change_summary as { trend?: string }).trend ?? "—")}
                </span>
              ) : null}
            </div>
            <TimeSeriesChart data={ts?.series ?? []} dark={dark} />
            {ts?.anomalies?.length ? (
              <div className="mt-3 text-xs text-amber-700 dark:text-amber-300">
                {ts.anomalies.slice(0, 3).map((a) => (
                  <div key={String(a.period)}>
                    {String(a.period)}: {String(a.detail)}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
