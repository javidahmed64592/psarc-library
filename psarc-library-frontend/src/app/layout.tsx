import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";

import "./globals.css";
import Footer from "@/components/Footer";
import Navigation from "@/components/Navigation";
import { AuthProvider } from "@/contexts/AuthContext";

export const metadata: Metadata = {
  title: "PSARC Library",
  description:
    "A web interface for parsing and exploring Rocksmith psarc files.",
  keywords: ["fastapi", "python", "react", "nextjs", "psarc", "rocksmith"],
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  // icons: {
  //   icon: [
  //     { url: "/icon.png", sizes: "192x192", type: "image/png" },
  //     { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
  //   ],
  //   apple: [{ url: "/apple-icon.png", sizes: "180x180", type: "image/png" }],
  //   other: [
  //     {
  //       rel: "android-chrome",
  //       url: "/android-icon-192x192.png",
  //       sizes: "192x192",
  //     },
  //   ],
  // },
  // manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: "#161b22",
                color: "#e6edf3",
                border: "1px solid #30363d",
                fontSize: "0.875rem",
              },
            }}
          />
          <div className="min-h-screen bg-background">
            <Navigation />
            <main className="container mx-auto px-4 py-4 pb-16">
              {children}
            </main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
