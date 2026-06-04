"use client";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { CheckCircle, ArrowRight, Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { createCheckout } from "@/lib/api";

export default function PricingPage() {
  const t = useTranslations("pricing");
  const locale = useLocale();
  const router = useRouter();
  const planKeys = ["free", "pro", "creator", "studio"] as const;
  const [loading, setLoading] = useState<string | null>(null);

  async function handlePlanClick(key: string) {
    if (key === "free") {
      router.push(`/${locale}/signup`);
      return;
    }
    if (key === "studio") {
      window.location.href = `mailto:hello@editclone.app?subject=Studioプランについて`;
      return;
    }
    setLoading(key);
    try {
      const origin = window.location.origin;
      const { checkout_url } = await createCheckout(
        key as "pro" | "creator",
        `${origin}/${locale}/dashboard`,
        `${origin}/${locale}/pricing`
      );
      window.location.href = checkout_url;
    } catch {
      router.push(`/${locale}/signup`);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="pt-24 pb-16 px-4">
        <div className="text-center mb-16 max-w-3xl mx-auto">
          <h1 className="text-5xl font-black text-gray-900 mb-4">{t("title")}</h1>
          <p className="text-gray-500 text-xl">{t("subtitle")}</p>
        </div>

        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {planKeys.map((key) => {
            const isHighlighted = key === "pro";
            const features = t.raw(`plans.${key}.features`) as string[];
            const isLoading = loading === key;

            return (
              <div
                key={key}
                className={`rounded-2xl p-6 border-2 transition-all relative ${
                  isHighlighted
                    ? "border-purple-500 bg-gradient-to-br from-purple-600 to-blue-600 text-white shadow-2xl shadow-purple-200"
                    : "border-gray-200 bg-white hover:border-purple-200 hover:shadow-lg"
                }`}
              >
                {isHighlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-amber-400 text-amber-900 text-xs font-bold rounded-full">
                    {t(`plans.${key}.badge`)}
                  </span>
                )}

                <h3 className={`font-black text-2xl mb-1 ${isHighlighted ? "text-white" : "text-gray-900"}`}>
                  {t(`plans.${key}.name`)}
                </h3>
                <p className={`text-sm mb-4 ${isHighlighted ? "text-white/80" : "text-gray-400"}`}>
                  {t(`plans.${key}.description`)}
                </p>

                <div className="flex items-baseline gap-1 mb-6">
                  <span className={`text-4xl font-black ${isHighlighted ? "text-white" : "text-gray-900"}`}>
                    {t(`plans.${key}.price`)}
                  </span>
                  <span className={`text-sm ${isHighlighted ? "text-white/70" : "text-gray-400"}`}>
                    /{t(`plans.${key}.period`)}
                  </span>
                </div>

                <ul className="space-y-3 mb-8">
                  {features.map((f: string) => (
                    <li key={f} className={`flex items-start gap-2 text-sm ${isHighlighted ? "text-white/90" : "text-gray-600"}`}>
                      <CheckCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isHighlighted ? "text-cyan-300" : "text-purple-500"}`} />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handlePlanClick(key)}
                  disabled={isLoading}
                  className={`flex items-center justify-center gap-2 w-full py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-70 ${
                    isHighlighted
                      ? "bg-white text-purple-700 hover:bg-purple-50"
                      : "bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:opacity-90"
                  }`}
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                  {t(`plans.${key}.cta`)}
                </button>
              </div>
            );
          })}
        </div>
      </main>
      <Footer />
    </div>
  );
}
