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
  // Kullanıcı uygulaması root'ta çalışır
};

module.exports = nextConfig;