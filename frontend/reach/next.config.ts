import withPWA from "next-pwa";

const nextConfig: any = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  experimental: {
    optimizePackageImports: ['@phosphor-icons/react'],
  },
};

// export default withPWA({
//   dest: "public",
//   disable: process.env.NODE_ENV === "development",
// })(nextConfig);

export default process.env.NODE_ENV === "development" 
  ? nextConfig 
  : withPWA({ dest: "public" })(nextConfig);