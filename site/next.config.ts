import type { NextConfig } from "next";

/* A static site: every home's result is precomputed by the Python pipeline into public/data.
   On GitHub Pages it lives under /square-deal; set BASE_PATH for that build. */
const basePath = process.env.BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
