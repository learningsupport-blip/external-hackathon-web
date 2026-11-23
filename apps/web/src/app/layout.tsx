import type { Metadata } from "next";
import { Bricolage_Grotesque, Figtree, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const body = Figtree({ subsets: ["latin"], variable: "--ff-body" });
const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--ff-display" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--ff-mono" });

export const metadata: Metadata = {
  title: { default: "HackHub", template: "%s · HackHub" },
  description: "External hackathons, entered once and shown across the site and calendar.",
};

export const preferredRegion = "bom1";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${body.variable} ${display.variable} ${mono.variable} h-full`}>
      <body className="min-h-full bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
