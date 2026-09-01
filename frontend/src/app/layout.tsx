import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AI Interviewer",
    template: "%s | AI Interviewer",
  },
  description: "Практика технических интервью с персональной обратной связью.",
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru">
      <body className="bg-canvas text-ink antialiased">{children}</body>
    </html>
  );
}
