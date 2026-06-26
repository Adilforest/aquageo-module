import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { apiGet } from "../../api/client";
import type { ByTerritory } from "../../api/stats";

export default function TerritoryBars() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [group, setGroup] = useState<"basin" | "district">("basin");
  const { data } = useQuery({
    queryKey: ["stats-by-territory", group],
    queryFn: () => apiGet<ByTerritory>(`/stats/by-territory/?group=${group}`),
  });
  const items = (data?.items ?? []).slice(0, 12);

  const onClick = (id: string) => navigate(`/?${group}=${id}`);

  return (
    <div>
      <div className="seg-toggle">
        <button className={group === "basin" ? "active" : ""} onClick={() => setGroup("basin")}>
          {t("dash.basin")}
        </button>
        <button className={group === "district" ? "active" : ""} onClick={() => setGroup("district")}>
          {t("dash.district")}
        </button>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={items} layout="vertical" margin={{ left: 20, right: 16 }}>
          <CartesianGrid horizontal={false} stroke="#eef2f5" />
          <XAxis type="number" allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar
            dataKey="count"
            fill="#2f73e0"
            cursor="pointer"
            onClick={(d: { id?: string }) => d?.id && onClick(d.id)}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
