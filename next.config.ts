import path from "path";
import type { NextConfig } from "next";

// In development the FastAPI backend is a separate uvicorn process on :8000.
// In production it is the Vercel Python function at api/index.py: the rewrite
// only selects that function, and the ASGI app still receives the original
// request path, so /api/search-runs matches the FastAPI route of the same name.
const isDev = process.env.NODE_ENV === "development";
const devApiTarget = process.env.API_PROXY_TARGET ?? process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Pin the tracing root to this repo so an unrelated lockfile in a parent
  // directory cannot be mistaken for the workspace root.
  outputFileTracingRoot: path.resolve(__dirname),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: isDev ? `${devApiTarget}/api/:path*` : "/api/index"
      },
      {
        source: "/health",
        destination: isDev ? `${devApiTarget}/health` : "/api/index"
      }
    ];
  }
};

export default nextConfig;
