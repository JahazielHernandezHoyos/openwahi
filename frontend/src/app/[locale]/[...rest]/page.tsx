import { notFound } from "next/navigation";

export default function LocaleCatchAllPage() {
  // Static and dynamic sibling routes take precedence over this catch-all.
  // Keeping it inside [locale] lets next-intl render the locale-specific 404.
  notFound();
}