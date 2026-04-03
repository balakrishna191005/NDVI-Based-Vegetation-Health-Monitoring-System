import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function TimeSeriesChart({
  data,
  dark,
}: {
  data: Array<{ date: string; mean_ndvi?: number | null }>;
  dark: boolean;
}) {
  const stroke = dark ? "#94a3b8" : "#64748b";
  const grid = dark ? "#334155" : "#e2e8f0";
  const filtered = data.filter((d) => d.mean_ndvi != null);
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={filtered} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={grid} />
          <XAxis dataKey="date" tick={{ fill: stroke, fontSize: 11 }} />
          <YAxis domain={[-0.2, 1]} tick={{ fill: stroke, fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: dark ? "#0f172a" : "#ffffff",
              borderColor: dark ? "#334155" : "#e2e8f0",
              borderRadius: 8,
            }}
          />
          <Line type="monotone" dataKey="mean_ndvi" stroke="#22c55e" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
