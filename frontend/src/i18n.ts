import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import kk from "./locales/kk.json";
import ru from "./locales/ru.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ru: { translation: ru },
      kk: { translation: kk },
      en: { translation: en },
    },
    fallbackLng: "ru",
    supportedLngs: ["ru", "kk", "en"],
    interpolation: { escapeValue: false },
    // RU is the default: only honor a previously chosen language, otherwise
    // fall back to RU (do not auto-switch to the browser language).
    detection: {
      order: ["localStorage"],
      caches: ["localStorage"],
    },
  });

export default i18n;
