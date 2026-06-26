import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { apiGet } from "../api/client";

interface Region {
  kato: string;
  name_ru: string;
  name_kk: string;
  name_en: string;
  count: number;
}

// Labels kept local to this control so it stays isolated (no shared-dict edits).
const LABELS: Record<string, { label: string; all: string }> = {
  ru: { label: "Область", all: "Все области" },
  kk: { label: "Облыс", all: "Барлық облыстар" },
  en: { label: "Region", all: "All regions" },
};

// Default scope on first load — Жамбылская область (matched by name).
const DEFAULT_REGION_NAME = "Жамбыл";

export default function RegionSwitcher() {
  const { i18n } = useTranslation();
  const lang = (i18n.resolvedLanguage ?? "ru") as "ru" | "kk" | "en";
  const [sp, setSp] = useSearchParams();
  const current = sp.get("region") ?? "";

  const { data: regions } = useQuery({
    queryKey: ["regions"],
    queryFn: () => apiGet<Region[]>("/regions/"),
  });

  const setRegion = (kato: string) =>
    setSp(
      (prev) => {
        const n = new URLSearchParams(prev);
        if (kato) n.set("region", kato);
        else n.delete("region");
        return n;
      },
      { replace: true },
    );

  // Default the scope to Жамбылская область ONCE per mount. Guarded by a ref so
  // that later choosing "All regions" (empty) is respected and not overridden.
  const didDefault = useRef(false);
  useEffect(() => {
    if (didDefault.current || !regions) return;
    didDefault.current = true;
    if (current) return; // URL already carries a region — keep it
    const def = regions.find((r) => r.name_ru.includes(DEFAULT_REGION_NAME));
    if (def) setRegion(def.kato);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions]);

  const labels = LABELS[lang] ?? LABELS.ru;
  const regionName = (r: Region) =>
    (lang === "kk" ? r.name_kk : lang === "en" ? r.name_en : r.name_ru) || r.name_ru;

  return (
    <label className="region-switch" title={labels.label}>
      <span className="material-symbols-outlined">public</span>
      <select
        value={current}
        aria-label={labels.label}
        onChange={(e) => setRegion(e.target.value)}
      >
        <option value="">{labels.all}</option>
        {(regions ?? []).map((r) => (
          <option key={r.kato} value={r.kato}>
            {regionName(r)} ({r.count})
          </option>
        ))}
      </select>
    </label>
  );
}
