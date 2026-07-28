import type { Metadata } from "next";
import { Instrument_Sans, Newsreader } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";

const interfaceFont = Instrument_Sans({ subsets: ["latin"], variable: "--font-interface", display: "swap" });
const editorialFont = Newsreader({ subsets: ["latin"], variable: "--font-editorial", display: "swap" });

export const metadata: Metadata = {
  title: "MyCasaPro",
  description: "Home maintenance coordination for homeowners and contractors.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${interfaceFont.variable} ${editorialFont.variable}`}>{children}</body>
    </html>
  );
}
