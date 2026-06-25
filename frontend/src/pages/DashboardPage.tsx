import { useTranslation } from "react-i18next";

// KPI cards and charts are added in issues #14 / #20.
export default function DashboardPage() {
  const { t } = useTranslation();
  return <div className="placeholder">{t("dashboard.title")}</div>;
}
