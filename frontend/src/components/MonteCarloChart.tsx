import {
  Area,
  ComposedChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface MonteCarloYearBand {
  year_index: number;
  p10: number;
  p50: number;
  p90: number;
}

export default function MonteCarloChart({ bands }: { bands: MonteCarloYearBand[] }) {
  const data = bands.map((b) => ({
    year: b.year_index,
    p10: b.p10,
    band: Math.max(0, b.p90 - b.p10),
    p50: b.p50,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="year"
          tickFormatter={(y) => `+${y}y`}
          stroke="var(--text-muted)"
          fontSize={12}
        />
        <YAxis
          tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
          stroke="var(--text-muted)"
          fontSize={12}
          width={60}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === "p50") return [`$${value.toLocaleString()}`, "Median (p50)"];
            return [`$${value.toLocaleString()}`, name];
          }}
          labelFormatter={(y) => `${y} year${y === 1 ? "" : "s"} from now`}
        />
        <Area
          type="monotone"
          dataKey="p10"
          stackId="band"
          stroke="none"
          fill="transparent"
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="band"
          stackId="band"
          name="p10–p90 range"
          stroke="none"
          fill="#2f855a"
          fillOpacity={0.15}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="p50"
          stroke="#2f855a"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
