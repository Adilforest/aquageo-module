import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { apiGet } from "../../api/client";
import type { LevelPoint } from "../../api/stats";

export default function LevelChart() {
  const { data } = useQuery({
    queryKey: ["stats-level-timeseries"],
    queryFn: () => apiGet<LevelPoint[]>("/stats/level-timeseries/?days=90"),
  });
  const rows = (data ?? []).map((p) => ({ date: p.date?.slice(5), avg_level: p.avg_level }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={rows} margin={{ left: 4, right: 16 }}>
        <CartesianGrid stroke="#eef2f5" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={28} />
        <YAxis tick={{ fontSize: 11 }} width={44} />
        <Tooltip />
        <Line type="monotone" dataKey="avg_level" stroke="#2f73e0" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
