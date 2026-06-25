import { useTranslation } from "react-i18next";

import KpiCards from "../components/KpiCards";

// Charts (by type / basin / dynamics) are added in issue #20.
export default function DashboardPage() {
  const { t } = useTranslation();
  return (
    <div style={{ overflowY: "auto", height: "100%" }}>
      <KpiCards />
      <div className="placeholder" style={{ paddingTop: 0 }}>
        {t("dashboard.chartsPlaceholder")}
      </div>
    </div>
  );
}
