import { useTranslation } from "react-i18next";

const LANGS = ["ru", "kk", "en"] as const;

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? "ru";
  return (
    <div className="lang-switch" role="group" aria-label="language">
      {LANGS.map((lng) => (
        <button
          key={lng}
          className={current === lng ? "active" : ""}
          onClick={() => i18n.changeLanguage(lng)}
        >
          {t(`lang.${lng}`)}
        </button>
      ))}
    </div>
  );
}
