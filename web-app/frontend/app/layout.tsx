import type { Metadata } from "next";
import { Saira_Condensed, Oswald } from "next/font/google";
import "./globals.css";

const saira = Saira_Condensed({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-saira"
});

const oswald = Oswald({
  subsets: ["latin"],
  variable: "--font-oswald"
});

export const metadata: Metadata = {
  title: "Fantasy Draft Pro",
  description: "Next Gen Draft Application",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${saira.variable} ${oswald.variable} antialiased bg-[#09090b] text-white`}
      >
        {children}
      </body>
    </html>
  );
}
