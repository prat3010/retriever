import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Retriever Client Reference",
  description: "Reference implementation for Retriever API integration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
