import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { CONDITION_COLORS, CONDITION_ORDER } from "../../theme";

// Same map/dashboard filters the report endpoint honors (type/condition are
// multi-value). Kept here so the export always mirrors the active view.
const FILTER_KEYS = ["type", "condition", "basin", "district", "search"];

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/** Build the absolute report URL for a format, carrying the active filters. */
export function reportUrl(format: "pdf" | "xlsx", filters: URLSearchParams): string {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    for (const value of filters.getAll(key)) {
      if (value) params.append(key, value);
    }
  }
  params.set("format", format);
  return `${API_BASE}/api/v1/reports/condition-summary/?${params.toString()}`;
}

export default function ReportsBlock() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const hasFilters = FILTER_KEYS.some((k) => searchParams.getAll(k).some(Boolean));

  return (
    <div className="dash-card wide reports-block">
      <div className="dash-card-title">
        <span className="material-symbols-outlined">summarize</span>
        {t("reports.title")}
      </div>
      <p className="reports-hint">
        {hasFilters ? t("reports.withFilters") : t("reports.allObjects")}
      </p>
      <div className="reports-actions">
        <a
          className="btn primary"
          href={reportUrl("pdf", searchParams)}
          data-testid="report-pdf"
          download
        >
          <span className="material-symbols-outlined">picture_as_pdf</span>
          {t("reports.exportPdf")}
        </a>
        <a
          className="btn"
          href={reportUrl("xlsx", searchParams)}
          data-testid="report-xlsx"
          download
        >
          <span className="material-symbols-outlined">table_view</span>
          {t("reports.exportExcel")}
        </a>
      </div>
      <div className="reports-legend">
        {CONDITION_ORDER.map((key) => (
          <span key={key} className="reports-legend-item">
            <span className="reports-legend-dot" style={{ background: CONDITION_COLORS[key] }} />
            {t(`condition.${key}`)}
          </span>
        ))}
      </div>
    </div>
  );
}
