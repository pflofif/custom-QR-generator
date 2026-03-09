import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "QR Platform",
  description: "Dynamic QR Code Management & Analytics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3500,
              style: { borderRadius: "10px", background: "#1e293b", color: "#f8fafc" },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}
