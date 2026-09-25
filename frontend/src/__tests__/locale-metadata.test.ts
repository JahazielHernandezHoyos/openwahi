import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { getLocaleMetadata } from "@/app/[locale]/metadata";
import { APP_NAME } from "@/config/brand";

describe("localized metadata", () => {
  it("uses English copy with the configured app name for /en", () => {
    const metadata = getLocaleMetadata("en");

    expect(metadata.title).toContain(APP_NAME);
    expect(metadata.description).toContain("Connect WhatsApp");
  });

  it("uses Spanish copy with the configured app name for /es", () => {
    const metadata = getLocaleMetadata("es");

    expect(metadata.title).toContain(APP_NAME);
    expect(metadata.description).toContain("Conecta tu WhatsApp");
  });

  it("only advertises icon assets that exist in public", () => {
    const icons = getLocaleMetadata("en").icons as {
      icon: { url: string }[];
    };

    expect(icons.icon.length).toBeGreaterThan(0);
    for (const { url } of icons.icon) {
      expect(existsSync(path.join(process.cwd(), "public", url))).toBe(true);
    }
  });
});
