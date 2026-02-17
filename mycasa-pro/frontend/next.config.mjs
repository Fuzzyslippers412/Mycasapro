import { dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable experimental Turbopack compatibility
  turbopack: {
    root: __dirname,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6709",
  },
  async redirects() {
    return [
      {
        source: "/profile",
        destination: "/settings?tab=profile",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
