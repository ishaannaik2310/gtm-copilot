import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GTM Ops Copilot — Fact-Checked Account Intelligence",
  description: "AI-driven researched and fact-checked account brief generator with deterministic claim auditing for high-velocity sales teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased font-sans text-slate-200 bg-obsidian-950 min-h-screen selection:bg-emerald-500/20 selection:text-emerald-300">
        {children}
      </body>
    </html>
  );
}
