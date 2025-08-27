/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { 
    unoptimized: true 
  },
  swcMinify: false,
  trailingSlash: true,
  // basePath artık gereksiz - subdomain'de root'ta çalışıyor
};

module.exports = nextConfig;