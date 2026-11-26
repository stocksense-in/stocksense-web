import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo root AGENTS.md already carries the Next.js notes; don't generate copies in frontend/.
  agentRules: false,
};

export default nextConfig;
