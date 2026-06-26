import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { apiGet } from "../../api/client";
import type { ByTypeRow } from "../../api/stats";

// Neutral palette for types — deliberately NOT the condition colors.
const NEUTRAL = [
  "#5b7186", "#7c93a8", "#9bb0c2", "#b9c8d6", "#6b8fb0",
  "#8aa6c0", "#aac0d4", "#c9d6e2", "#4a6076", "#a0aebb", "#d3dde6",
];

export default function TypeDonut() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["stats-by-type"],
    queryFn: () => apiGet<ByTypeRow[]>("/stats/by-type/"),
  });
  const rows = (data ?? []).map((r, i) => ({
    code: r.type,
    name: t(`types.${r.type}`, { defaultValue: r.type_name }),
    value: r.count,
    fill: NEUTRAL[i % NEUTRAL.length],
  }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={rows}
          dataKey="value"
          nameKey="name"
          innerRadius={55}
          outerRadius={88}
          paddingAngle={1}
          onClick={(d: { code?: string }) => d?.code && navigate(`/?type=${d.code}`)}
          cursor="pointer"
        >
          {rows.map((r) => (
            <Cell key={r.code} fill={r.fill} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
