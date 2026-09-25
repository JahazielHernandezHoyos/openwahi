import { describe, expect, it } from "vitest";
import { getSafeHttpUrl } from "@/lib/safeUrls";

describe("getSafeHttpUrl", () => {
  it.each(["https://example.com/hook", "http://localhost:8000/hook"])(
    "accepts HTTP(S) webhook URLs: %s",
    (url) => expect(getSafeHttpUrl(url)).toBe(url),
  );

  it.each([
    "javascript:alert(1)",
    "file:///etc/passwd",
    "https://user:password@example.com/hook",
  ])("rejects non-HTTP or credentialed URLs: %s", (url) => {
    expect(getSafeHttpUrl(url)).toBeNull();
  });
});
