import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { apiGet } from "../api/client";
import { CONDITION_COLORS, CONDITION_ORDER } from "../theme";

interface Opt {
  id?: string;
  kato?: string;
  code?: string;
  name_ru: string;
}

// Shares the map's query-param contract (#11): type/condition (multi),
// basin/district (single), search, needs_geocoding. Resets page on change.
export default function CatalogFilters() {
  const { t } = useTranslation();
  const [sp, setSp] = useSearchParams();

  const basins = useQuery({ queryKey: ["basins"], queryFn: () => apiGet<Opt[]>("/basins/") });
  const districts = useQuery({
    queryKey: ["districts"],
    queryFn: () => apiGet<Opt[]>("/admin-units/?level=district"),
  });
  const types = useQuery({
    queryKey: ["object-types"],
    queryFn: () => apiGet<Opt[]>("/object-types/"),
  });

  const selectedConditions = sp.getAll("condition");

  const update = (mut: (n: URLSearchParams) => void) =>
    setSp(
      (prev) => {
        const n = new URLSearchParams(prev);
        mut(n);
        n.delete("page"); // any filter change returns to page 1
        return n;
      },
      { replace: true },
    );

  const toggleMulti = (key: string, val: string) =>
    update((n) => {
      const set = new Set(n.getAll(key));
      n.delete(key);
      set.has(val) ? set.delete(val) : set.add(val);
      [...set].forEach((v) => n.append(key, v));
    });

  const setSingle = (key: string, val: string) =>
    update((n) => (val ? n.set(key, val) : n.delete(key)));

  const [searchText, setSearchText] = useState(sp.get("search") ?? "");
  useEffect(() => {
    const id = setTimeout(() => setSingle("search", searchText.trim()), 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  const needsGeo = sp.get("needs_geocoding") === "true";

  return (
    <div className="cat-filters">
      <input
        className="fp-search cat-search"
        type="search"
        placeholder={t("filters.search")}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
      />
      <div className="fp-chips">
        {CONDITION_ORDER.map((c) => {
          const active = selectedConditions.includes(c);
          return (
            <button
              key={c}
              className={`chip${active ? " active" : ""}`}
              style={active ? { background: CONDITION_COLORS[c], borderColor: CONDITION_COLORS[c] } : {}}
              onClick={() => toggleMulti("condition", c)}
            >
              <span className="chip-dot" style={{ background: CONDITION_COLORS[c] }} />
              {t(`condition.${c}`)}
            </button>
          );
        })}
      </div>
      <select className="fp-select cat-select" value={sp.get("type") ?? ""}
              onChange={(e) => update((n) => { n.delete("type"); if (e.target.value) n.append("type", e.target.value); })}>
        <option value="">{t("legend.types")}: {t("filters.all")}</option>
        {(types.data ?? []).map((o) => (
          <option key={o.code} value={o.code}>{t(`types.${o.code}`, { defaultValue: o.name_ru })}</option>
        ))}
      </select>
      <select className="fp-select cat-select" value={sp.get("basin") ?? ""}
              onChange={(e) => setSingle("basin", e.target.value)}>
        <option value="">{t("filters.basin")}: {t("filters.all")}</option>
        {(basins.data ?? []).map((b) => <option key={b.id} value={b.id}>{b.name_ru}</option>)}
      </select>
      <select className="fp-select cat-select" value={sp.get("district") ?? ""}
              onChange={(e) => setSingle("district", e.target.value)}>
        <option value="">{t("filters.district")}: {t("filters.all")}</option>
        {(districts.data ?? []).map((d) => <option key={d.kato} value={d.kato}>{d.name_ru}</option>)}
      </select>
      <label className="cat-geo-toggle">
        <input
          type="checkbox"
          checked={needsGeo}
          onChange={(e) => setSingle("needs_geocoding", e.target.checked ? "true" : "")}
        />
        {t("catalog.onlyNeedsGeocoding")}
      </label>
      <button
        className="fp-reset cat-reset"
        disabled={[...sp.keys()].length === 0}
        onClick={() => { setSearchText(""); setSp(new URLSearchParams(), { replace: true }); }}
      >
        {t("filters.reset")}
      </button>
    </div>
  );
}
