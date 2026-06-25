import { useTranslation } from "react-i18next";

import { CONDITION_COLORS, CONDITION_ORDER, TYPE_ICONS } from "../theme";

export default function Legend({ types }: { types: string[] }) {
  const { t } = useTranslation();
  return (
    <div className="legend">
      <h4>{t("legend.condition")}</h4>
      {CONDITION_ORDER.map((c) => (
        <div className="row" key={c}>
          <span className="dot" style={{ background: CONDITION_COLORS[c] }} />
          {t(`condition.${c}`)}
        </div>
      ))}
      {types.length > 0 && (
        <>
          <h4 style={{ marginTop: 12 }}>{t("legend.types")}</h4>
          {types.map((code) => (
            <div className="row" key={code}>
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                {TYPE_ICONS[code] ?? "place"}
              </span>
              {t(`types.${code}`, { defaultValue: code })}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
