import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AuthControl from "./AuthControl";
import LanguageSwitcher from "./LanguageSwitcher";

const NAV = [
  { to: "/", key: "map", icon: "map" },
  { to: "/catalog", key: "catalog", icon: "table_rows" },
  { to: "/dashboard", key: "dashboard", icon: "monitoring" },
];

const TITLE_BY_PATH: Record<string, string> = {
  "/": "map.title",
  "/catalog": "catalog.title",
  "/dashboard": "dashboard.title",
};

export default function Layout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="material-symbols-outlined" style={{ fontSize: 28 }}>
            water_drop
          </span>
          <span>
            <b>{t("app.title")}</b>
            <small>{t("app.subtitle")}</small>
          </span>
        </div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            {t(`nav.${item.key}`)}
          </NavLink>
        ))}
      </aside>
      <div className="main">
        <header className="header">
          <h1>{t(TITLE_BY_PATH[pathname] ?? "app.title")}</h1>
          <div className="header-actions">
            <AuthControl />
            <LanguageSwitcher />
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
