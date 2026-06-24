"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

/**
 * Toast Notification System — context-based toasts.
 *
 * WHY a context instead of a global store (Zustand, Redux)?
 * Toasts are lightweight ephemeral UI. A React context with
 * auto-dismiss timers is the simplest approach with zero deps.
 *
 * Usage:
 *   const { toast } = useToast();
 *   toast("Application deleted", "success");
 *   toast("Something went wrong", "error");
 */

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export const useToast = () => useContext(ToastContext);

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);

    // Auto-dismiss after 3.5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const dismiss = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  /** Map toast type to emoji + colors */
  const getStyle = (type: ToastType) => {
    const styles: Record<ToastType, { icon: string; bg: string; border: string }> = {
      success: { icon: "✅", bg: "rgba(34, 197, 94, 0.12)", border: "rgba(34, 197, 94, 0.3)" },
      error:   { icon: "❌", bg: "rgba(239, 68, 68, 0.12)", border: "rgba(239, 68, 68, 0.3)" },
      warning: { icon: "⚠️", bg: "rgba(234, 179, 8, 0.12)", border: "rgba(234, 179, 8, 0.3)" },
      info:    { icon: "ℹ️", bg: "rgba(59, 130, 246, 0.12)", border: "rgba(59, 130, 246, 0.3)" },
    };
    return styles[type];
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast container — fixed bottom-right */}
      {toasts.length > 0 && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            maxWidth: 380,
          }}
        >
          {toasts.map((t) => {
            const s = getStyle(t.type);
            return (
              <div
                key={t.id}
                onClick={() => dismiss(t.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "12px 16px",
                  borderRadius: 12,
                  background: s.bg,
                  border: `1px solid ${s.border}`,
                  backdropFilter: "blur(16px)",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "var(--text-primary, #fff)",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                  animation: "toastSlideIn 0.3s ease-out",
                }}
              >
                <span style={{ fontSize: "1.125rem", flexShrink: 0 }}>{s.icon}</span>
                <span style={{ flex: 1 }}>{t.message}</span>
                <span style={{ opacity: 0.5, fontSize: "0.75rem" }}>✕</span>
              </div>
            );
          })}
        </div>
      )}
    </ToastContext.Provider>
  );
}
