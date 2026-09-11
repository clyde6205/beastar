/**
 * BeAstar mobile — i18n bootstrap
 * ==================================
 * Bundles the same locale catalogs the backend uses (app/i18n/locales/) so
 * error/status strings match between API responses and client-rendered
 * UI text. Only 'en' and 'tl' are populated for the same reason the
 * backend only ships those two: no frontend existed to translate for
 * until now, and the PH soft launch only needs those two.
 *
 * Add more languages by dropping a matching JSON file in this folder and
 * adding it to the `resources` map below and SUPPORTED_LOCALES.
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import tl from './locales/tl.json';

export const SUPPORTED_LOCALES = ['en', 'tl'] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

i18n.use(initReactI18next).init({
  compatibilityJSON: 'v3',
  resources: {
    en: { translation: en },
    tl: { translation: tl },
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
