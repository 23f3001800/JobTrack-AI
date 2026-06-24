"use client";

import { ToastProvider } from "@/components/Toast";

/**
 * Client-side Providers wrapper.
 *
 * WHY a separate file? Next.js App Router root layouts are Server
 * Components by default. Context providers (like ToastProvider)
 * require "use client". This wrapper keeps the root layout as a
 * Server Component while providing client-side contexts.
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
