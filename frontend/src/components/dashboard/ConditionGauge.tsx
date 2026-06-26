import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";

import { apiGet } from "../../api/client";
import type { ByCondition } from "../../api/stats";
import { CONDITION_COLORS, CONDITION_ORDER } from "../../theme";

function indexColor(index: number): string {
  if (index >= 75) return CONDITION_COLORS.serviceable;
  if (index >= 50) return CONDITION_COLORS.monitoring;
  if (index >= 25) return CONDITION_COLORS.repair;
  return CONDITION_COLORS.emergency;
}

export default function ConditionGauge() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["stats-by-condition"],
    queryFn: () => apiGet<ByCondition>("/stats/by-condition/"),
  });
  const index = data?.index ?? 0;
  const counts = data?.counts ?? {};

  return (
    <div>
      <div className="gauge-wrap">
        <ResponsiveContainer width="100%" height={150}>
          <RadialBarChart
            innerRadius="75%"
            outerRadius="100%"
            data={[{ value: index, fill: indexColor(index) }]}
            startAngle={180}
            endAngle={0}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={10} background />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="gauge-value">
          <b>{index}</b>
          <small>{t("dash.healthIndex")}</small>
        </div>
      </div>
      <div className="cond-legend">
        {CONDITION_ORDER.map((c) => (
          <button key={c} className="cond-row" onClick={() => navigate(`/?condition=${c}`)}>
            <span className="dot" style={{ background: CONDITION_COLORS[c] }} />
            <span className="cond-name">{t(`condition.${c}`)}</span>
            <b>{counts[c] ?? 0}</b>
          </button>
        ))}
      </div>
    </div>
  );
}
