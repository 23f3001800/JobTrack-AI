import { redirect } from "next/navigation";

/**
 * Root page — redirects to dashboard.
 *
 * WHY server-side redirect instead of client-side?
 * Faster UX — no flash of empty content. The browser gets a 307
 * redirect header before any JavaScript loads.
 */
export default function Home() {
  redirect("/login");
}
