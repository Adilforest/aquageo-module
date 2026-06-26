import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { apiGet } from "../api/client";
import CatalogFilters from "../components/CatalogFilters";
import { conditionColor } from "../theme";
import type { Paginated, StructureListItem } from "../types";

const PAGE_SIZE = 20;
const SORTABLE: { key: string; label: string }[] = [
  { key: "name_ru", label: "cols.name" },
  { key: "commissioning_year", label: "cols.year" },
  { key: "wear_percent", label: "cols.wear" },
];

export default function CatalogPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();

  const params = new URLSearchParams(sp);
  params.set("page_size", String(PAGE_SIZE));
  const page = Number(sp.get("page") || 1);
  const ordering = sp.get("ordering") || "";
  const qs = params.toString();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["catalog", qs],
    queryFn: () => apiGet<Paginated<StructureListItem>>(`/structures/?${qs}`),
    placeholderData: (p) => p,
  });

  const total = data?.count ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const setParam = (key: string, val: string) =>
    setSp((prev) => {
      const n = new URLSearchParams(prev);
      val ? n.set(key, val) : n.delete(key);
      return n;
    }, { replace: true });

  const toggleSort = (key: string) => {
    const next = ordering === key ? `-${key}` : ordering === `-${key}` ? "" : key;
    setSp((prev) => {
      const n = new URLSearchParams(prev);
      next ? n.set("ordering", next) : n.delete("ordering");
      n.delete("page");
      return n;
    }, { replace: true });
  };

  const sortMark = (key: string) =>
    ordering === key ? " ▲" : ordering === `-${key}` ? " ▼" : "";

  return (
    <div className="catalog">
      <CatalogFilters />
      <div className="cat-meta">
        {isError ? t("map.error") : t("catalog.found", { count: total })}
      </div>
      <div className="cat-table-wrap">
        <table className="cat-table">
          <thead>
            <tr>
              {SORTABLE.map((c) => (
                <th key={c.key} className="sortable" onClick={() => toggleSort(c.key)}>
                  {t(`catalog.${c.label}`)}{sortMark(c.key)}
                </th>
              ))}
              <th>{t("catalog.cols.type")}</th>
              <th>{t("catalog.cols.condition")}</th>
              <th>{t("catalog.cols.basin")}</th>
              <th>{t("catalog.cols.district")}</th>
              <th>{t("catalog.cols.flag")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((r) => (
              <tr key={r.id} className="cat-row" onClick={() => navigate(`/structures/${r.id}`)}>
                <td>{r.name_ru}</td>
                <td>{r.commissioning_year ?? "—"}</td>
                <td>{r.wear_percent ?? "—"}</td>
                <td>{t(`types.${r.type}`, { defaultValue: r.type_name })}</td>
                <td>
                  <span className="badge sm" style={{ background: conditionColor(r.condition_status) }}>
                    {t(`condition.${r.condition_status}`, { defaultValue: t("condition.nodata") })}
                  </span>
                </td>
                <td>{r.basin_name ?? "—"}</td>
                <td>{r.admin_unit_name ?? "—"}</td>
                <td>
                  {r.needs_geocoding ? (
                    <span className="geo-flag">
                      <span className="material-symbols-outlined" style={{ fontSize: 15 }}>
                        wrong_location
                      </span>
                      {t("catalog.needsGeocoding")}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
            {!isLoading && (data?.results?.length ?? 0) === 0 && (
              <tr>
                <td colSpan={8} className="cat-empty">—</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="cat-pager">
        <button disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>‹</button>
        <span>{page} / {pages}</span>
        <button disabled={page >= pages} onClick={() => setParam("page", String(page + 1))}>›</button>
      </div>
    </div>
  );
}
