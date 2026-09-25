/**
 * Vitest global test setup
 * Provides jsdom environment, mocks for Next.js, and shared test utilities
 */
import "@testing-library/jest-dom/vitest";

// Keep unit tests independent from developer shell configuration. Individual
// tests can still override this value before re-importing a module.
process.env.NEXT_PUBLIC_API_URL ??= "http://localhost:8000";

// ---------------------------------------------------------------------------
// Mock: next/navigation (App Router)
// ---------------------------------------------------------------------------
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/es/dashboard",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ locale: "es" }),
}));

// ---------------------------------------------------------------------------
// Mock: next-intl
// ---------------------------------------------------------------------------
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => "es"),
}));

// ---------------------------------------------------------------------------
// Mock: next/image
// ---------------------------------------------------------------------------
vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    const { fill, priority, ...rest } = props;
    return <img {...(rest as React.ImgHTMLAttributes<HTMLImageElement>)} />;
  },
}));
