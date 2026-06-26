import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { ApiError, apiGet, apiSend } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canEdit } from "../auth/roles";
import { conditionColor, typeIcon } from "../theme";
import type { StructureDetail, WaterBodyOption } from "../types";

const SIGNIFICANCE = ["republican", "regional", "district", "local"];

function coordsLabel(geom: StructureDetail["geom"]): string {
  if (!geom) return "—";
  if (geom.type === "Point") {
    const [lon, lat] = geom.coordinates as [number, number];
    return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }
  return geom.type;
}

export default function ObjectCard({ id }: { id: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const editable = canEdit(user?.role);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["structure", id],
    queryFn: () => apiGet<StructureDetail>(`/structures/${id}/`),
    placeholderData: (prev) => prev, // avoid blank flash while refetching
  });

  const waterBodies = useQuery({
    queryKey: ["water-bodies"],
    queryFn: () => apiGet<WaterBodyOption[]>("/water-bodies/"),
    enabled: editable,
  });

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [attrs, setAttrs] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setEditing(false);
  }, [id]);

  const startEdit = () => {
    if (!data) return;
    setForm({
      name_ru: data.name_ru,
      name_kk: data.name_kk,
      name_en: data.name_en,
      commissioning_year: data.commissioning_year ?? "",
      responsible_org: data.responsible_org,
      significance: data.significance,
      water_body: data.water_body ?? "",
    });
    setAttrs({ ...data.attributes });
    setErrors({});
    setEditing(true);
  };

  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        name_ru: form.name_ru,
        name_kk: form.name_kk,
        name_en: form.name_en,
        commissioning_year: form.commissioning_year === "" ? null : Number(form.commissioning_year),
        responsible_org: form.responsible_org,
        significance: form.significance,
        water_body: form.water_body === "" ? null : form.water_body,
        attributes: { ...data!.attributes, ...attrs },
      };
      return apiSend<StructureDetail>(`/structures/${id}/`, "PATCH", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["structure", id] });
      qc.invalidateQueries({ queryKey: ["structures-geojson"] });
      setEditing(false);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.data && typeof err.data === "object") {
        const fieldErrors: Record<string, string> = {};
        for (const [k, v] of Object.entries(err.data as Record<string, unknown>)) {
          fieldErrors[k] = Array.isArray(v) ? String(v[0]) : String(v);
        }
        setErrors(fieldErrors);
      } else {
        setErrors({ _: t("card.saveError") });
      }
    },
  });

  if (isLoading) return <aside className="object-card">{t("map.loading")}</aside>;
  if (isError || !data)
    return (
      <aside className="object-card">
        <button className="card-close" onClick={() => navigate("/")}>
          ✕
        </button>
        {t("map.error")}
      </aside>
    );

  const schemaProps = data.type_detail?.schema?.properties ?? {};

  return (
    <aside className="object-card">
      <button className="card-close" onClick={() => navigate("/")} aria-label="close">
        ✕
      </button>

      <div className="card-photo">
        {data.type ? (
          <span className="material-symbols-outlined" style={{ fontSize: 56, color: "#9fb2c4" }}>
            {typeIcon(data.type)}
          </span>
        ) : null}
        <span className="card-photo-note">{t("card.noPhoto")}</span>
      </div>

      {!editing ? (
        <ViewMode data={data} schemaProps={schemaProps} editable={editable} onEdit={startEdit} />
      ) : (
        <form
          className="card-edit"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          {errors._ && <div className="field-error">{errors._}</div>}
          <Field label={t("card.nameRu")} error={errors.name_ru}>
            <input
              value={String(form.name_ru ?? "")}
              onChange={(e) => setForm({ ...form, name_ru: e.target.value })}
            />
          </Field>
          <Field label={t("card.nameKk")}>
            <input
              value={String(form.name_kk ?? "")}
              onChange={(e) => setForm({ ...form, name_kk: e.target.value })}
            />
          </Field>
          <Field label={t("card.nameEn")}>
            <input
              value={String(form.name_en ?? "")}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
            />
          </Field>
          <Field label={t("card.year")} error={errors.commissioning_year}>
            <input
              type="number"
              value={String(form.commissioning_year ?? "")}
              onChange={(e) => setForm({ ...form, commissioning_year: e.target.value })}
            />
          </Field>
          <Field label={t("card.responsibleOrg")}>
            <input
              value={String(form.responsible_org ?? "")}
              onChange={(e) => setForm({ ...form, responsible_org: e.target.value })}
            />
          </Field>
          <Field label={t("card.significance")}>
            <select
              value={String(form.significance ?? "")}
              onChange={(e) => setForm({ ...form, significance: e.target.value })}
            >
              <option value="">—</option>
              {SIGNIFICANCE.map((s) => (
                <option key={s} value={s}>
                  {t(`significance.${s}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("card.waterObject")}>
            <select
              value={String(form.water_body ?? "")}
              onChange={(e) => setForm({ ...form, water_body: e.target.value })}
            >
              <option value="">—</option>
              {(waterBodies.data ?? []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name_ru}
                </option>
              ))}
            </select>
          </Field>

          <div className="card-section-title">{t("card.techParams")}</div>
          {Object.entries(schemaProps).map(([key, prop]) => (
            <Field key={key} label={prop.title ?? key} error={errors.attributes}>
              {prop.type === "boolean" ? (
                <input
                  type="checkbox"
                  checked={Boolean(attrs[key])}
                  onChange={(e) => setAttrs({ ...attrs, [key]: e.target.checked })}
                />
              ) : (
                <input
                  type={prop.type === "number" || prop.type === "integer" ? "number" : "text"}
                  value={attrs[key] === undefined || attrs[key] === null ? "" : String(attrs[key])}
                  onChange={(e) =>
                    setAttrs({
                      ...attrs,
                      [key]:
                        prop.type === "number" || prop.type === "integer"
                          ? e.target.value === ""
                            ? null
                            : Number(e.target.value)
                          : e.target.value,
                    })
                  }
                />
              )}
            </Field>
          ))}
          {errors.attributes && <div className="field-error">{errors.attributes}</div>}

          <Field label={t("card.condition")}>
            <input disabled value={t(`condition.${data.condition_status}`, { defaultValue: "—" })} />
          </Field>

          <div className="card-actions">
            <button type="submit" className="btn primary" disabled={save.isPending}>
              {t("card.save")}
            </button>
            <button type="button" className="btn" onClick={() => setEditing(false)}>
              {t("card.cancel")}
            </button>
          </div>
        </form>
      )}
    </aside>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="card-field">
      <span className="card-field-label">{label}</span>
      {children}
      {error && <span className="field-error">{error}</span>}
    </label>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card-row">
      <span className="card-row-label">{label}</span>
      <span className="card-row-value">{value}</span>
    </div>
  );
}

function ViewMode({
  data,
  schemaProps,
  editable,
  onEdit,
}: {
  data: StructureDetail;
  schemaProps: Record<string, { type?: string; title?: string }>;
  editable: boolean;
  onEdit: () => void;
}) {
  const { t } = useTranslation();
  const attrEntries = Object.entries(data.attributes ?? {});
  const inspections = data.inspections ?? [];
  const attachments = data.attachments ?? [];
  return (
    <>
      <div className="card-title-row">
        <h2>{data.name_ru}</h2>
        <span
          className="badge"
          style={{ background: conditionColor(data.condition_status) }}
        >
          {t(`condition.${data.condition_status}`, { defaultValue: t("condition.nodata") })}
        </span>
      </div>
      <div className="card-type">
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
          {typeIcon(data.type)}
        </span>
        {t(`types.${data.type}`, { defaultValue: data.type_name })}
      </div>

      <Row label={t("card.waterObject")} value={data.water_body_name ?? "—"} />
      <Row label={t("card.coordinates")} value={coordsLabel(data.geom)} />
      <Row label={t("card.year")} value={data.commissioning_year ?? "—"} />
      <Row label={t("card.basin")} value={data.basin_name ?? "—"} />
      <Row label={t("card.district")} value={data.admin_unit_name ?? "—"} />
      <Row label={t("card.responsibleOrg")} value={data.responsible_org || "—"} />
      <Row
        label={t("card.significance")}
        value={data.significance ? t(`significance.${data.significance}`) : "—"}
      />

      <div className="card-section-title">{t("card.techParams")}</div>
      {attrEntries.length === 0 ? (
        <div className="card-empty">—</div>
      ) : (
        attrEntries
          .filter(([k]) => k !== "source_key")
          .map(([key, value]) => (
            <Row
              key={key}
              label={schemaProps[key]?.title ?? key}
              value={value === null || value === undefined ? "—" : String(value)}
            />
          ))
      )}

      <div className="card-section-title">{t("card.inspections")}</div>
      {inspections.length === 0 ? (
        <div className="card-empty">{t("card.noInspections")}</div>
      ) : (
        inspections.map((i) => (
          <div className="card-inspection" key={i.id}>
            <b>{i.inspected_at}</b> · {i.inspector || "—"}
            {i.condition_observed && (
              <span style={{ color: conditionColor(i.condition_observed), marginLeft: 6 }}>
                ● {t(`condition.${i.condition_observed}`, { defaultValue: i.condition_observed })}
              </span>
            )}
          </div>
        ))
      )}

      <div className="card-section-title">{t("card.documents")}</div>
      {attachments.length === 0 ? (
        <div className="card-empty">{t("card.noDocuments")}</div>
      ) : (
        attachments.map((a) => (
          <div className="card-doc" key={a.id}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              description
            </span>
            {a.file_url ? (
              <a href={a.file_url} target="_blank" rel="noreferrer">
                {t(`attachment.${a.kind}`, { defaultValue: a.kind })}
              </a>
            ) : (
              t(`attachment.${a.kind}`, { defaultValue: a.kind })
            )}
          </div>
        ))
      )}

      {editable && (
        <div className="card-actions">
          <button className="btn primary" onClick={onEdit}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              edit
            </span>
            {t("card.edit")}
          </button>
        </div>
      )}
    </>
  );
}
