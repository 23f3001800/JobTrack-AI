"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { isLoggedIn, clearTokens } from "@/lib/api";

/**
 * Dashboard Layout — sidebar navigation + main content area.
 *
 * WHY a nested layout instead of a single layout?
 * Only authenticated pages need the sidebar. The login page
 * should be full-screen. Next.js nested layouts let us split
 * these concerns cleanly.
 *
 * The sidebar is fixed-position with nav links. Active state
 * is determined by comparing the current pathname.
 */

/** Navigation items with emoji icons (no icon library needed) */
const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/dashboard/new", label: "New Application", icon: "🚀" },
  { href: "/dashboard/tracker", label: "Tracker", icon: "📋" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
    }
  }, [router]);

  const handleLogout = () => {
    clearTokens();
    router.push("/login");
  };

  return (
    <div className="layout">
      {/* ──────── Sidebar ──────── */}
      <aside className="sidebar">
        {/* Logo */}
        <Link href="/dashboard" className="sidebar-logo">
          🎯 <span>JobTrack AI</span>
        </Link>

        {/* Navigation */}
        <nav>
          <ul className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`sidebar-link ${
                    pathname === item.href ? "active" : ""
                  }`}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Spacer pushes logout to bottom */}
        <div style={{ flex: 1 }} />

        {/* Logout */}
        <button
          className="btn btn-ghost"
          onClick={handleLogout}
          style={{ width: "100%" }}
        >
          🚪 Sign Out
        </button>
      </aside>

      {/* ──────── Main Content ──────── */}
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
