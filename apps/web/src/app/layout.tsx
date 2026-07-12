import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Retriever Playground",
  description: "Grounded memory layer and query playground UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
