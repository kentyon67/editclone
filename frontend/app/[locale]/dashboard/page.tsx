"use client";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { Upload, Film, Zap, ChevronRight } from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const PLAN_LIMITS: Record<string, number> = { free: 3, pro: 30, creator: 100, studio: Infinity };

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale();

  const plan = "free";
  const usedThisMonth = 0;
  const limit = PLAN_LIMITS[plan];
  const remaining = limit === Infinity ? "∞" : limit - usedThisMonth;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-black text-gray-900">{t("title")}</h1>
          <p className="text-gray-500 mt-1">{t("subtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-2xl p-5 border border-purple-100 shadow-sm">
            <p className="text-sm text-gray-500 mb-1">{t("plan")}</p>
            <p className="text-2xl font-black text-purple-600 capitalize">{plan}</p>
          </div>
          <div className="bg-white rounded-2xl p-5 border border-purple-100 shadow-sm">
            <p className="text-sm text-gray-500 mb-1">{t("remaining")}</p>
            <p className="text-2xl font-black text-gray-900">{remaining} <span className="text-sm font-normal text-gray-400">/ {limit === Infinity ? "∞" : limit}</span></p>
          </div>
          <div className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-2xl p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-white/70 mb-1">{t("upgrade")}</p>
              <p className="text-white font-bold">Pro ¥980/月</p>
            </div>
            <Link href={`/${locale}/pricing`} className="bg-white/20 hover:bg-white/30 text-white rounded-xl p-2 transition-colors">
              <ChevronRight className="w-5 h-5" />
            </Link>
          </div>
        </div>

        <Link
          href={`/${locale}/upload`}
          className="flex items-center justify-center gap-3 w-full py-16 rounded-2xl border-2 border-dashed border-purple-300 bg-purple-50 hover:bg-purple-100 hover:border-purple-400 transition-all group mb-8"
        >
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
              <Upload className="w-8 h-8 text-white" />
            </div>
            <span className="text-lg font-bold text-purple-700">{t("upload")}</span>
            <span className="text-sm text-gray-400">MP4, MOV, M4V</span>
          </div>
        </Link>

        <div className="text-center text-gray-400 py-12">
          <Film className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="font-medium">{t("noVideos")}</p>
          <p className="text-sm">{t("noVideosSub")}</p>
        </div>
      </main>

      <Footer />
    </div>
  );
}
