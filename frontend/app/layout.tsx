import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GTM Copilot — Account Intelligence & Grounded Outreach",
  description: "Enterprise sales intelligence & verifiable cold outreach generator with deterministic claim auditing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased font-display text-[var(--text-primary)] bg-[var(--bg-void)] min-h-[100dvh] selection:bg-amber-500/20 selection:text-amber-200">
        {children}
      </body>
    </html>
  );
}
