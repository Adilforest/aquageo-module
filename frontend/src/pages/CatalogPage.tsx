import { useTranslation } from "react-i18next";

export default function CatalogPage() {
  const { t } = useTranslation();
  return <div className="placeholder">{t("catalog.placeholder")}</div>;
}
