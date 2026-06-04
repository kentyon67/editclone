import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { Inter } from "next/font/google";
import "../globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EditClone — AI編集アシスタント for Final Cut Pro",
  description: "動画をアップロードするだけ。AIが編集スタイルを分析し、FCPXML・字幕・チャプターを自動生成します。",
  openGraph: {
    title: "EditClone",
    description: "AI Editing Assistant for Final Cut Pro",
    siteName: "EditClone",
  },
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className={inter.className}>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
