import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Giám sát xâm nhập mạng",
  description: "Phát hiện tấn công mạng và đề xuất biện pháp ứng phó bằng mô hình HC-CLOSR",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
