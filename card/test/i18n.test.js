import { describe, expect, it } from "vitest";
import { resolveLang, STRINGS, t } from "../src/i18n.js";

describe("STRINGS", () => {
  it("every language has exactly the same keys as English", () => {
    const enKeys = Object.keys(STRINGS.en).sort();
    for (const [lang, dict] of Object.entries(STRINGS)) {
      if (lang === "en") continue;
      expect(Object.keys(dict).sort(), `language "${lang}"`).toEqual(enKeys);
    }
  });
});

describe("resolveLang", () => {
  it("picks an exact supported match", () => {
    expect(resolveLang({ locale: { language: "he" } })).toBe("he");
    expect(resolveLang({ locale: { language: "pt-BR" } })).toBe("pt-BR");
  });

  it("falls back to the base language for an unsupported region variant", () => {
    expect(resolveLang({ locale: { language: "de-AT" } })).toBe("de");
    expect(resolveLang({ locale: { language: "pt-PT" } })).toBe("pt-BR");
  });

  it("falls back to English for an unsupported language", () => {
    expect(resolveLang({ locale: { language: "ja" } })).toBe("en");
  });

  it("falls back to English when hass/locale is missing", () => {
    expect(resolveLang(undefined)).toBe("en");
    expect(resolveLang({})).toBe("en");
  });

  it("supports the legacy hass.language fallback", () => {
    expect(resolveLang({ language: "fr" })).toBe("fr");
  });
});

describe("t", () => {
  it("translates a known key", () => {
    expect(t("de", "badge_live")).toBe("Live");
    expect(t("he", "badge_resolved")).toBe("נפתר");
  });

  it("substitutes placeholders", () => {
    expect(t("en", "footer_ends", { date: "Nov 3, 2026" })).toBe("Ends Nov 3, 2026");
  });

  it("falls back to English for an unsupported language", () => {
    expect(t("xx", "badge_live")).toBe("Live");
  });

  it("falls back to the raw key when missing everywhere", () => {
    expect(t("en", "no_such_key")).toBe("no_such_key");
  });
});
