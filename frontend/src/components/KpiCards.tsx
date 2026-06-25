import { useQueries } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { apiGet } from "../api/client";
import { CONDITION_COLORS } from "../theme";

interface CountResponse {
  count: number;
}

// total + the four condition buckets, each count read from the API (paginated
// `count`, page_size=1 to keep the payload tiny).
const CARDS = [
  { key: "total", color: "#2f73e0", query: "" },
  { key: "serviceable", color: CONDITION_COLORS.serviceable, query: "&condition_status=serviceable" },
  { key: "monitoring", color: CONDITION_COLORS.monitoring, query: "&condition_status=monitoring" },
  { key: "repair", color: CONDITION_COLORS.repair, query: "&condition_status=repair" },
  { key: "emergency", color: CONDITION_COLORS.emergency, query: "&condition_status=emergency" },
] as const;

export default function KpiCards() {
  const { t } = useTranslation();
  const results = useQueries({
    queries: CARDS.map((c) => ({
      queryKey: ["kpi-count", c.key],
      queryFn: () => apiGet<CountResponse>(`/structures/?page_size=1${c.query}`),
    })),
  });

  return (
    <div className="kpi-grid">
      {CARDS.map((c, i) => {
        const q = results[i];
        return (
          <div className="kpi-card" key={c.key} style={{ borderLeftColor: c.color }}>
            <div className="value" style={{ color: c.color }}>
              {q.isLoading ? "…" : q.isError ? "—" : (q.data?.count ?? 0)}
            </div>
            <div className="label">{t(`kpi.${c.key}`)}</div>
          </div>
        );
      })}
    </div>
  );
}
