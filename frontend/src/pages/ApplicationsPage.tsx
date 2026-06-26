import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, apiGet, apiSend } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ROLE_RANK } from "../auth/roles";
import "./ApplicationsPage.css";

// Isolated gov-flow screen (issue #30): applications list + decision card.
// Inline RU strings + scoped CSS; shared dictionaries/header/map untouched
// (only an additive nav entry + route).

interface Signature {
  id: string;
  signer: string;
  signed_at: string;
  cert_subject: string;
  valid: boolean;
}

interface ApprovalOrder {
  id: string;
  number: string;
  file: string;
  issued_at: string;
}

interface Application {
  id: string;
  structure: string;
  structure_name: string | null;
  kind: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  submitted_by: string | null;
  submitted_by_username: string | null;
  reviewer: string | null;
  reviewer_username: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  comment: string;
  created_at: string;
  signature: Signature | null;
  order: ApprovalOrder | null;
}

interface Paginated<T> {
  count: number;
  results: T[];
}

interface StructureDetail {
  id: string;
  name_ru: string;
  status: string;
  commissioning_year: number | null;
  wear_percent: number | null;
  responsible_org: string | null;
}

const STATUS: Record<Application["status"], { label: string; color: string }> = {
  draft: { label: "Черновик", color: "#8C97A7" },
  submitted: { label: "На согласовании", color: "#E0921E" },
  approved: { label: "Согласовано", color: "#1F9D57" },
  rejected: { label: "Отклонено", color: "#E0443E" },
};

const KIND_LABEL: Record<string, string> = {
  create: "Создание",
  update: "Изменение",
  decommission: "Вывод из эксплуатации",
};

const LIFECYCLE_LABEL: Record<string, string> = {
  draft: "Черновик",
  pending_review: "На согласовании",
  published: "Опубликован",
  archived: "В архиве",
};

const FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Все" },
  { value: "submitted", label: "На согласовании" },
  { value: "approved", label: "Согласовано" },
  { value: "rejected", label: "Отклонено" },
  { value: "draft", label: "Черновики" },
];

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

function StatusBadge({ status }: { status: Application["status"] }) {
  const s = STATUS[status] ?? STATUS.draft;
  return (
    <span className="app-badge" style={{ background: s.color }}>
      {s.label}
    </span>
  );
}

export default function ApplicationsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isManager = (ROLE_RANK[user?.role ?? ""] ?? -1) >= ROLE_RANK.manager;

  const [status, setStatus] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionMsg, setActionMsg] = useState("");
  const [comment, setComment] = useState("");

  const qs = status ? `?status=${status}` : "";
  const { data, isLoading, isError } = useQuery({
    queryKey: ["applications", qs],
    queryFn: () => apiGet<Paginated<Application>>(`/applications/${qs}`),
  });

  // Engineers see only their own; managers/admins see everything.
  const rows = (data?.results ?? []).filter(
    (a) => isManager || a.submitted_by_username === user?.username,
  );
  const selected = rows.find((a) => a.id === selectedId) ?? null;

  const decide = async (decision: "approve" | "reject") => {
    if (!selected) return;
    setBusy(true);
    setActionMsg("");
    try {
      await apiSend<Application>(`/applications/${selected.id}/decide/`, "POST", {
        decision,
        comment,
      });
      await qc.invalidateQueries({ queryKey: ["applications"] });
      await qc.invalidateQueries({ queryKey: ["structure", selected.structure] });
      setComment("");
      setActionMsg(decision === "approve" ? "Заявка согласована ✓" : "Заявка отклонена");
    } catch (e) {
      setActionMsg(
        e instanceof ApiError && e.status === 403
          ? "Решение доступно только руководителю"
          : "Не удалось выполнить действие",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app-page">
      <div className="app-toolbar">
        <h2 style={{ margin: 0 }}>Согласование заявок</h2>
        <div className="app-filters">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className={`app-chip${status === f.value ? " active" : ""}`}
              onClick={() => setStatus(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {!user && <p className="app-note">Войдите, чтобы видеть заявки.</p>}
      {isError && <p className="app-error">Не удалось загрузить заявки.</p>}
      {isLoading && <p className="app-note">Загрузка…</p>}

      <div className="app-layout">
        <div className="app-list">
          <table className="app-table">
            <thead>
              <tr>
                <th>Объект</th>
                <th>Тип</th>
                <th>Статус</th>
                <th>Заявитель</th>
                <th>Подана</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr
                  key={a.id}
                  className={a.id === selectedId ? "selected" : ""}
                  onClick={() => {
                    setSelectedId(a.id);
                    setActionMsg("");
                  }}
                >
                  <td>{a.structure_name ?? a.structure.slice(0, 8)}</td>
                  <td>{KIND_LABEL[a.kind] ?? a.kind}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td>{a.submitted_by_username ?? "—"}</td>
                  <td>{fmt(a.submitted_at)}</td>
                </tr>
              ))}
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="app-note" style={{ textAlign: "center" }}>
                    Заявок нет.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {selected && (
          <DecisionCard
            app={selected}
            isManager={isManager}
            busy={busy}
            comment={comment}
            actionMsg={actionMsg}
            onComment={setComment}
            onDecide={decide}
          />
        )}
      </div>
    </div>
  );
}

function DecisionCard({
  app,
  isManager,
  busy,
  comment,
  actionMsg,
  onComment,
  onDecide,
}: {
  app: Application;
  isManager: boolean;
  busy: boolean;
  comment: string;
  actionMsg: string;
  onComment: (v: string) => void;
  onDecide: (d: "approve" | "reject") => void;
}) {
  const { data: structure } = useQuery({
    queryKey: ["structure", app.structure],
    queryFn: () => apiGet<StructureDetail>(`/structures/${app.structure}/`),
  });
  const canDecide = isManager && app.status === "submitted";

  return (
    <div className="app-card">
      <div className="app-card-head">
        <h3 style={{ margin: 0 }}>{app.structure_name ?? "Объект"}</h3>
        <StatusBadge status={app.status} />
      </div>

      <section className="app-section">
        <h4>Объект-черновик</h4>
        <dl className="app-dl">
          <dt>Тип заявки</dt><dd>{KIND_LABEL[app.kind] ?? app.kind}</dd>
          <dt>Заявитель</dt><dd>{app.submitted_by_username ?? "—"}</dd>
          <dt>Подана</dt><dd>{fmt(app.submitted_at)}</dd>
          {structure && (
            <>
              <dt>Год ввода</dt><dd>{structure.commissioning_year ?? "—"}</dd>
              <dt>Износ, %</dt><dd>{structure.wear_percent ?? "—"}</dd>
              <dt>Ответственная орг.</dt><dd>{structure.responsible_org ?? "—"}</dd>
              <dt>Жизненный цикл</dt>
              <dd>
                <b>{LIFECYCLE_LABEL[structure.status] ?? structure.status}</b>{" "}
                <Link to={`/structures/${app.structure}`}>на карте</Link>
              </dd>
            </>
          )}
        </dl>
        {app.comment && <p className="app-note">Комментарий: {app.comment}</p>}
      </section>

      {canDecide && (
        <section className="app-section">
          <h4>Решение руководителя</h4>
          <textarea
            className="app-comment"
            placeholder="Комментарий (необязательно)"
            value={comment}
            onChange={(e) => onComment(e.target.value)}
          />
          <div className="app-actions">
            <button className="app-btn approve" disabled={busy} onClick={() => onDecide("approve")}>
              Согласовать
            </button>
            <button className="app-btn reject" disabled={busy} onClick={() => onDecide("reject")}>
              Отклонить
            </button>
          </div>
          {actionMsg && <p className="app-note">{actionMsg}</p>}
        </section>
      )}

      {app.status === "approved" && (
        <section className="app-section app-approved">
          <h4>Согласовано</h4>
          {app.signature && (
            <p className="app-note">
              <span className="material-symbols-outlined app-ico">verified</span>
              Подписано (ЭЦП-заглушка): <code>{app.signature.cert_subject}</code>
              {app.reviewer_username && <> · {app.reviewer_username}</>}
            </p>
          )}
          {app.order ? (
            <p className="app-note">
              <span className="material-symbols-outlined app-ico">description</span>
              Приказ {app.order.number} —{" "}
              <a href={app.order.file} target="_blank" rel="noreferrer">скачать PDF</a>
            </p>
          ) : (
            <p className="app-note">Приказ генерируется…</p>
          )}
          <p className="app-note app-published">
            Объект опубликован и виден на карте/в каталоге.
          </p>
        </section>
      )}

      {app.status === "rejected" && (
        <section className="app-section">
          <p className="app-note">Заявка отклонена{app.reviewer_username ? ` (${app.reviewer_username})` : ""}.</p>
        </section>
      )}
    </div>
  );
}
