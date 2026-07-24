import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // A calculadora nasce como rota do site (favorece SEO e herda autoridade de
  // domínio — pergunta em aberto nº 3 do PRD). Se a decisão for subdomínio
  // (roi.setima.cc), basta remover o basePath.
  // basePath: '/calculadora',
};

export default nextConfig;
