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
      <body className="antialiased font-sans text-neutral-100 bg-black min-h-[100dvh] selection:bg-neutral-800 selection:text-white">
        {children}
      </body>
    </html>
  );
}
