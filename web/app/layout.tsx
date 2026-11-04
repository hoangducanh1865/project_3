import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";

const sans = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Giám sát xâm nhập mạng",
  description: "Phát hiện tấn công mạng và đề xuất biện pháp ứng phó",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" className={`${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
