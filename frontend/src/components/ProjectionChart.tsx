import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface YearProjection {
  year_index: number;
  phase: string;
  balance: number;
}

export default function ProjectionChart({
  timeline,
  yearsToRetirement,
}: {
  timeline: YearProjection[];
  yearsToRetirement: number;
}) {
  const data = timeline.map((t) => ({
    year: t.year_index,
    balance: t.balance,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <defs>
          <linearGradient id="balanceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2f855a" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#2f855a" stopOpacity={0.02} />
          </linearGradient>
        </defs>
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
          formatter={(value: number) => [`$${value.toLocaleString()}`, "Balance"]}
          labelFormatter={(y) => `${y} year${y === 1 ? "" : "s"} from now`}
        />
        <ReferenceLine
          x={yearsToRetirement}
          stroke="var(--accent)"
          strokeDasharray="4 4"
          label={{ value: "Retirement", position: "top", fill: "var(--accent)", fontSize: 12 }}
        />
        <Area
          type="monotone"
          dataKey="balance"
          stroke="#2f855a"
          strokeWidth={2}
          fill="url(#balanceFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
