/** @type {import('next').NextConfig} */
const nextConfig = {
  // "standalone" produces a self-contained server.js in .next/standalone/
  // that includes only the necessary node_modules. Required for the Docker
  // production build — reduces image size from ~500 MB to ~100 MB.
  output: "standalone",
  reactCompiler: true,
};

export default nextConfig;
