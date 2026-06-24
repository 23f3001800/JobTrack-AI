import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Providers from "./providers";
import "./globals.css";

/**
 * WHY Inter font?
 * Inter is designed specifically for screens — it has excellent
 * legibility at small sizes, tabular number support (for stats),
 * and a clean, modern feel that matches our design language.
 */
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "JobTrack AI — Intelligent Job Application Agent",
  description:
    "AI-powered multi-agent system that scrapes jobs, researches companies, writes personalised cover letters, and tracks your applications.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
