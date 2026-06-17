import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Mission Control Ops Runtime",
  description: "Customer operations dashboard for workflow intake, review, receipts, and replay."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
