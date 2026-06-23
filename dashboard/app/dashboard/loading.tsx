/**
 * Loading state for dashboard pages.
 *
 * Next.js App Router shows this component while a page's
 * data is being fetched. Uses our design system's skeleton
 * animation for a polished loading experience.
 */

export default function DashboardLoading() {
  return (
    <div className="animate-fade-in">
      {/* Page header skeleton */}
      <div style={{ marginBottom: "var(--space-xl)" }}>
        <div
          className="skeleton"
          style={{ height: 32, width: 200, marginBottom: "var(--space-sm)" }}
        />
        <div className="skeleton" style={{ height: 18, width: 300 }} />
      </div>

      {/* Stats cards skeleton */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "var(--space-md)",
          marginBottom: "var(--space-xl)",
        }}
      >
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton" style={{ height: 100 }} />
        ))}
      </div>

      {/* Content skeleton */}
      <div className="skeleton" style={{ height: 300 }} />
    </div>
  );
}
