import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/proxy/:path*",
        destination: "https://rag.prateeq.in/:path*",
      },
    ];
  },
};

export default nextConfig;
