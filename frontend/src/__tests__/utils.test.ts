/**
 * Tests for lib/utils - cn() utility
 */
import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn()", () => {
  it("merges class names", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
  });

  it("handles conditional classes via clsx", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("resolves tailwind conflicts (last wins)", () => {
    // tailwind-merge resolves px-4 vs px-2 -> px-2
    const result = cn("px-4", "px-2");
    expect(result).toBe("px-2");
  });

  it("handles undefined and null inputs", () => {
    expect(cn("a", undefined, null, "b")).toBe("a b");
  });

  it("returns empty string for no inputs", () => {
    expect(cn()).toBe("");
  });

  it("merges array inputs", () => {
    expect(cn(["a", "b"], "c")).toBe("a b c");
  });
});
