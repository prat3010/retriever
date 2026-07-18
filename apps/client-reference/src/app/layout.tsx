import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Retriever — API Reference & Curl Examples",
  description: "Curl-based API reference for the Retriever RAG engine. Includes search, chat, and document management endpoints.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
