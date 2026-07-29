import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const internalAPIURL = process.env.MYCASAPRO_INTERNAL_API_URL || "http://localhost:8081";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    useTypeScriptCli: true,
  },
  turbopack: {
    root: rootDir,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalAPIURL}/api/:path*`,
      },
      {
        source: "/healthz",
        destination: `${internalAPIURL}/healthz`,
      },
    ];
  },
};

export default nextConfig;
