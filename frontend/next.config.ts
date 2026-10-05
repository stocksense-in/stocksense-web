import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Old URLs from the first version of the site keep working.
  async redirects() {
    return [
      { source: '/analysis', destination: '/stocks', permanent: true },
      { source: '/geopolitics-engine', destination: '/geopolitics', permanent: true },
      { source: '/mf', destination: '/dashboard', permanent: false },
    ];
  },
};

export default nextConfig;
