"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isLoggedIn, clearTokens, getCurrentUser, getProfile } from "@/lib/api";

/**
 * Dashboard Layout — sidebar navigation + main content area.
 *
 * WHY a nested layout instead of a single layout?
 * Only authenticated pages need the sidebar. The login page
 * should be full-screen. Next.js nested layouts let us split
 * these concerns cleanly.
 *
 * Mobile: sidebar slides in from the left with a hamburger toggle.
 * An overlay backdrop dims the main content when sidebar is open.
 */

/** Navigation items shown to every authenticated user */
const USER_NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/dashboard/search", label: "Search & Apply", icon: "🔍" },
  { href: "/dashboard/tracker", label: "Tracker", icon: "📋" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

/** Admin-only navigation items */
const ADMIN_NAV = [
  { href: "/dashboard/admin", label: "Admin", icon: "🛡️" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Redirect to login if not authenticated, or to onboarding if not completed
  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }
    // Check onboarding status
    getProfile().then((profile) => {
      const p = profile as { onboarding_complete?: boolean } | null;
      if (p && !p.onboarding_complete) {
        router.push("/onboarding");
      }
    }).catch(() => {}); // Ignore errors (API might be down)
  }, [router]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    clearTokens();
    router.push("/login");
  };

  // Build nav items based on user role
  const user = getCurrentUser();
  const navItems = user?.role === "admin" ? [...USER_NAV, ...ADMIN_NAV] : USER_NAV;

  return (
    <div className="layout">
      {/* ──────── Mobile Header ──────── */}
      <div className="mobile-header">
        <button
          className="hamburger-btn"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open menu"
        >
          ☰
        </button>
        <Link href="/dashboard" style={{ textDecoration: "none", color: "var(--text-primary)", fontWeight: 600 }}>
          🎯 AutoApply AI
        </Link>
        <div style={{ width: 32 }} /> {/* Spacer for centering */}
      </div>

      {/* ──────── Sidebar Overlay (mobile) ──────── */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? "visible" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* ──────── Sidebar ──────── */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        {/* Logo */}
        <Link href="/dashboard" className="sidebar-logo">
          🎯 <span>AutoApply AI</span>
        </Link>

        {/* Navigation */}
        <nav>
          <ul className="sidebar-nav">
            {navItems.map((item) => (
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
