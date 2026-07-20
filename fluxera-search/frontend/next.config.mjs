/** @type {import('next').NextConfig} */
const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

const nextConfig = {
	// Allow uploads up to 50 MB (matches backend upload_max_mb).
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
		},
	},
	async rewrites() {
		return [
			{
				source: "/api/:path*",
				destination: `${backendInternalUrl}/:path*`
			}
		];
	}
};

export default nextConfig;
