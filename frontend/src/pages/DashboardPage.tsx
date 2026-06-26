import { useTranslation } from "react-i18next";

import KpiCards from "../components/KpiCards";
import ConditionGauge from "../components/dashboard/ConditionGauge";
import LevelChart from "../components/dashboard/LevelChart";
import ReportsBlock from "../components/dashboard/ReportsBlock";
import RiskBlock from "../components/dashboard/RiskBlock";
import TerritoryBars from "../components/dashboard/TerritoryBars";
import TypeDonut from "../components/dashboard/TypeDonut";

function Card({ title, children, wide }: { title: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={`dash-card${wide ? " wide" : ""}`}>
      <div className="dash-card-title">{title}</div>
      {children}
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  return (
    <div className="dashboard">
      <KpiCards />
      <div className="dash-grid">
        <Card title={t("dash.byType")}>
          <TypeDonut />
        </Card>
        <Card title={t("dash.condition")}>
          <ConditionGauge />
        </Card>
        <Card title={t("dash.byTerritory")}>
          <TerritoryBars />
        </Card>
        <RiskBlock />
        <Card title={t("dash.level")} wide>
          <LevelChart />
        </Card>
        <ReportsBlock />
      </div>
    </div>
  );
}
