import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { apiGet } from "../../api/client";
import type { RiskSummary } from "../../api/stats";
import { CONDITION_COLORS } from "../../theme";

// Risk level -> color (reuse the shared condition palette for consistency).
const LEVEL_COLOR: Record<string, string> = {
  critical: CONDITION_COLORS.emergency,
  high: CONDITION_COLORS.repair,
  watch: CONDITION_COLORS.monitoring,
  none: CONDITION_COLORS.serviceable,
};
const ORDER = ["critical", "high", "watch", "none"];

function Levels({ title, data }: { title: string; data: Record<string, number> }) {
  const { t } = useTranslation();
  return (
    <div className="risk-levels">
      <div className="risk-sub">{title}</div>
      <div className="risk-chips">
        {ORDER.filter((lv) => data[lv]).map((lv) => (
          <span key={lv} className="risk-chip" style={{ background: LEVEL_COLOR[lv] }}>
            {t(`risk.${lv}`)}: {data[lv]}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function RiskBlock() {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ["stats-risk-summary"],
    queryFn: () => apiGet<RiskSummary>("/stats/risk-summary/"),
  });
  if (!data) return null;
  return (
    <div className="risk-block">
      <div className="risk-header">
        <span className="material-symbols-outlined">flood</span>
        {t("dash.risk")}
      </div>
      <div className="risk-body">
        <div className="risk-forecast">
          <b>{data.forecast_crossing}</b>
          <span>{t("dash.forecastCrossing")}</span>
        </div>
        <Levels title={t("dash.flood")} data={data.flood} />
        <Levels title={t("dash.lowWater")} data={data.low_water} />
      </div>
    </div>
  );
}
