import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { apiGet } from "../api/client";
import { CONDITION_COLORS, CONDITION_ORDER } from "../theme";

interface BasinOpt {
  id: string;
  name_ru: string;
}
interface AdminUnitOpt {
  kato: string;
  name_ru: string;
}
interface ObjectTypeOpt {
  code: string;
  name_ru: string;
}

export default function FilterPanel({ count }: { count: number }) {
  const { t } = useTranslation();
  const [sp, setSp] = useSearchParams();

  const basins = useQuery({ queryKey: ["basins"], queryFn: () => apiGet<BasinOpt[]>("/basins/") });
  const districts = useQuery({
    queryKey: ["districts"],
    queryFn: () => apiGet<AdminUnitOpt[]>("/admin-units/?level=district"),
  });
  const types = useQuery({
    queryKey: ["object-types"],
    queryFn: () => apiGet<ObjectTypeOpt[]>("/object-types/"),
  });

  const selectedConditions = sp.getAll("condition");
  const selectedTypes = sp.getAll("type");

  const toggleMulti = (key: string, val: string) =>
    setSp(
      (prev) => {
        const n = new URLSearchParams(prev);
        const set = new Set(n.getAll(key));
        n.delete(key);
        set.has(val) ? set.delete(val) : set.add(val);
        [...set].forEach((v) => n.append(key, v));
        return n;
      },
      { replace: true },
    );

  const setSingle = (key: string, val: string) =>
    setSp(
      (prev) => {
        const n = new URLSearchParams(prev);
        val ? n.set(key, val) : n.delete(key);
        return n;
      },
      { replace: true },
    );

  // Debounced free-text search synced to the URL.
  const [searchText, setSearchText] = useState(sp.get("search") ?? "");
  useEffect(() => {
    const id = setTimeout(() => setSingle("search", searchText.trim()), 350);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  const reset = () => {
    setSearchText("");
    setSp(new URLSearchParams(), { replace: true });
  };

  const hasFilters = [...sp.keys()].length > 0;

  return (
    <div className="filter-panel">
      <div className="fp-head">
        <strong>{t("filters.title")}</strong>
        <span className="fp-count">{t("map.count", { count })}</span>
      </div>

      <input
        className="fp-search"
        type="search"
        placeholder={t("filters.search")}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
      />

      <div className="fp-group-title">{t("legend.condition")}</div>
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

      <div className="fp-group-title">{t("legend.types")}</div>
      <div className="fp-chips">
        {(types.data ?? []).map((ot) => {
          const active = selectedTypes.includes(ot.code);
          return (
            <button
              key={ot.code}
              className={`chip type${active ? " active" : ""}`}
              onClick={() => toggleMulti("type", ot.code)}
            >
              {t(`types.${ot.code}`, { defaultValue: ot.name_ru })}
            </button>
          );
        })}
      </div>

      <div className="fp-group-title">{t("filters.basin")}</div>
      <select
        className="fp-select"
        value={sp.get("basin") ?? ""}
        onChange={(e) => setSingle("basin", e.target.value)}
      >
        <option value="">{t("filters.all")}</option>
        {(basins.data ?? []).map((b) => (
          <option key={b.id} value={b.id}>
            {b.name_ru}
          </option>
        ))}
      </select>

      <div className="fp-group-title">{t("filters.district")}</div>
      <select
        className="fp-select"
        value={sp.get("district") ?? ""}
        onChange={(e) => setSingle("district", e.target.value)}
      >
        <option value="">{t("filters.all")}</option>
        {(districts.data ?? []).map((d) => (
          <option key={d.kato} value={d.kato}>
            {d.name_ru}
          </option>
        ))}
      </select>

      <button className="fp-reset" onClick={reset} disabled={!hasFilters}>
        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
          restart_alt
        </span>
        {t("filters.reset")}
      </button>
    </div>
  );
}
