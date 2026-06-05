import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/travel-ai",
  serverExternalPackages: ["@libsql/client"],
};

export default nextConfig;
