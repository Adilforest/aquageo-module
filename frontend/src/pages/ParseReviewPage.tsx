import { useState } from "react";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";

import { ApiError, apiSend, getToken } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { canEdit } from "../auth/roles";
import "./ParseReviewPage.css";

// Isolated screen (issue #24): inline RU strings, scoped CSS — does not touch
// the shared dictionaries/header/map.

const CONF_COLOR: Record<string, string> = {
  high: "#1F9D57",
  medium: "#E0921E",
  low: "#8C97A7",
};

interface ParseJob {
  id: string;
  status: string;
  raw_extract: Record<string, unknown>;
  confidence: Record<string, string>;
  result_structure: string | null;
  match_status: string;
  matched_structure: string | null;
  error_message?: string;
}

const MATCH_BADGE: Record<string, { text: string; color: string }> = {
  new: { text: "Новый объект", color: "#1F9D57" },
  existing: { text: "Уже есть в базе", color: "#2F73E0" },
  needs_check: { text: "Требует проверки", color: "#E0921E" },
};

const FIELD_LABELS: Record<string, string> = {
  name_ru: "Название",
  latitude: "Широта",
  longitude: "Долгота",
  commissioning_year: "Год ввода",
  responsible_org: "Ответственная организация",
  danger_level: "Опасный уровень",
  river: "Река",
  datum_m: "Нуль поста, м",
};

export default function ParseReviewPage() {
  const { user } = useAuth();
  const editable = canEdit(user?.role);

  const [file, setFile] = useState<File | null>(null);
  const [objectType, setObjectType] = useState("hydropost");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState<ParseJob | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitMsg, setSubmitMsg] = useState("");

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    setSubmitMsg("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("object_type", objectType);
      const token = getToken();
      const res = await fetch("/api/v1/parse-jobs/", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setError(res.status === 403 ? "Нужны права инженера (войдите как инженер)" :
          (data?.detail ?? `Ошибка ${res.status}`));
        return;
      }
      setJob(data);
      const init: Record<string, string> = {};
      Object.entries(data.raw_extract ?? {}).forEach(([k, v]) => (init[k] = v == null ? "" : String(v)));
      setValues(init);
    } catch {
      setError("Не удалось загрузить файл");
    } finally {
      setBusy(false);
    }
  };

  const submitForApproval = async () => {
    if (!job?.result_structure) return;
    setSubmitMsg("");
    try {
      const app = await apiSend<{ id: string }>("/applications/", "POST", {
        structure: job.result_structure,
        kind: "create",
        comment: "Черновик из ИИ-парсинга документа",
      });
      await apiSend(`/applications/${app.id}/submit/`, "POST", {});
      setSubmitMsg("Заявка на согласование отправлена ✓");
    } catch (e) {
      setSubmitMsg(
        e instanceof ApiError && e.status === 403
          ? "Подача заявки доступна инженеру (войдите)"
          : "Не удалось отправить заявку",
      );
    }
  };

  const lat = Number(values.latitude);
  const lon = Number(values.longitude);
  const hasCoords = Number.isFinite(lat) && Number.isFinite(lon) && (lat !== 0 || lon !== 0);
  const badge = job ? MATCH_BADGE[job.match_status] : null;

  return (
    <div className="parse-page">
      <h2 style={{ marginTop: 0 }}>ИИ-парсинг документа</h2>

      <div className="parse-upload">
        <select value={objectType} onChange={(e) => setObjectType(e.target.value)}>
          <option value="hydropost">Гидропост</option>
          <option value="dam">Плотина</option>
          <option value="canal">Канал</option>
          <option value="reservoir">Водохранилище</option>
        </select>
        <input
          type="file"
          accept=".xlsx,.xls,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button className="parse-btn" onClick={upload} disabled={!file || busy}>
          {busy ? "Распознаём…" : "Распознать"}
        </button>
        {!editable && <span className="parse-note">Для загрузки войдите как инженер.</span>}
      </div>
      {error && <p className="parse-error">{error}</p>}

      {job && job.status === "error" && (
        <p className="parse-error">Ошибка разбора: {job.error_message}</p>
      )}

      {job && job.status === "done" && (
        <>
          <div className="parse-grid">
            <div className="parse-card">
              <h3 style={{ marginTop: 0 }}>Извлечённые поля</h3>
              <p className="parse-legend">
                <span><i className="conf-dot" style={{ background: CONF_COLOR.high }} /> высокая</span>
                <span><i className="conf-dot" style={{ background: CONF_COLOR.medium }} /> средняя</span>
                <span><i className="conf-dot" style={{ background: CONF_COLOR.low }} /> низкая</span>
              </p>
              {Object.keys(values)
                .filter((k) => k !== "source_key" && k !== "osm_id")
                .map((k) => (
                  <div className="parse-field" key={k}>
                    <span
                      className="conf-dot"
                      title={job.confidence?.[k] ?? "low"}
                      style={{ background: CONF_COLOR[job.confidence?.[k] ?? "low"] }}
                    />
                    <label>{FIELD_LABELS[k] ?? k}</label>
                    <input
                      value={values[k]}
                      onChange={(e) => setValues({ ...values, [k]: e.target.value })}
                    />
                  </div>
                ))}
            </div>

            <div className="parse-card">
              <h3 style={{ marginTop: 0 }}>Сверка с базой</h3>
              {badge && (
                <span className="match-badge" style={{ background: badge.color }}>
                  {badge.text}
                </span>
              )}
              {job.match_status !== "new" && job.matched_structure && (
                <p className="parse-note" style={{ marginTop: 8 }}>
                  Найденный объект:{" "}
                  <Link to={`/structures/${job.matched_structure}`}>открыть карточку</Link>
                </p>
              )}
              {hasCoords && (
                <div className="parse-mini-map" style={{ marginTop: 12 }}>
                  <MapContainer center={[lat, lon]} zoom={11} style={{ height: "100%" }}>
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    <CircleMarker center={[lat, lon]} radius={9}
                      pathOptions={{ color: "#2F73E0", fillColor: "#2F73E0", fillOpacity: 0.6 }} />
                  </MapContainer>
                </div>
              )}
            </div>
          </div>

          <div style={{ marginTop: 16, display: "flex", gap: 10, alignItems: "center" }}>
            <button className="parse-btn" onClick={submitForApproval} disabled={!editable}>
              Отправить на согласование
            </button>
            {submitMsg && <span className="parse-note">{submitMsg}</span>}
          </div>
        </>
      )}
    </div>
  );
}
