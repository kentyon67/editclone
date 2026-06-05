import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import {
  Scissors, FileText, BookOpen, Film, Captions, Zap,
  ArrowRight, CheckCircle,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

// 固定値でハイドレーションエラーを防ぐ
const BUBBLES = [
  { w: 284, h: 192, l: 78, t: 12 }, { w: 156, h: 348, l: 23, t: 67 },
  { w: 320, h: 210, l: 45, t: 85 }, { w: 98, h: 260, l: 62, t: 32 },
  { w: 240, h: 140, l: 9, t: 50 },  { w: 180, h: 320, l: 88, t: 71 },
  { w: 350, h: 180, l: 55, t: 18 }, { w: 120, h: 290, l: 34, t: 92 },
  { w: 270, h: 230, l: 72, t: 55 }, { w: 200, h: 160, l: 15, t: 28 },
  { w: 310, h: 270, l: 41, t: 76 }, { w: 140, h: 200, l: 93, t: 42 },
  { w: 220, h: 310, l: 67, t: 8 },  { w: 170, h: 130, l: 28, t: 61 },
  { w: 260, h: 250, l: 81, t: 90 }, { w: 190, h: 180, l: 52, t: 38 },
  { w: 130, h: 340, l: 7, t: 80 },  { w: 300, h: 160, l: 38, t: 22 },
  { w: 160, h: 220, l: 95, t: 58 }, { w: 230, h: 290, l: 18, t: 45 },
];

function Hero() {
  const t = useTranslations("hero");
  const locale = useLocale();
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-purple-950 via-indigo-900 to-blue-900">
      <div className="absolute inset-0 animate-gradient-x bg-gradient-to-r from-purple-900 via-violet-800 to-blue-900 opacity-60" />
      <div className="absolute inset-0">
        {BUBBLES.map((b, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white/5"
            style={{
              width: `${b.w}px`,
              height: `${b.h}px`,
              left: `${b.l}%`,
              top: `${b.t}%`,
              transform: "translate(-50%,-50%)",
            }}
          />
        ))}
      </div>

      <div className="relative z-10 text-center px-4 max-w-5xl mx-auto animate-fade-in-up">
        <span className="inline-block mb-6 px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full text-white/90 text-sm font-medium">
          {t("badge")}
        </span>

        <h1 className="text-5xl md:text-7xl font-black text-white mb-6 leading-tight tracking-tight">
          {t("title")}
          <br />
          <span className="bg-gradient-to-r from-cyan-300 via-purple-300 to-pink-300 bg-clip-text text-transparent">
            {t("titleAccent")}
          </span>
        </h1>

        <p className="text-xl text-white/80 mb-10 max-w-2xl mx-auto leading-relaxed">
          {t("description")}
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href={`/${locale}/signup`}
            className="flex items-center gap-2 px-8 py-4 bg-white text-purple-700 font-bold rounded-xl hover:bg-purple-50 transition-all shadow-xl shadow-purple-900/50 text-lg"
          >
            {t("cta")} <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-white/50 text-sm">{t("ctaSub")}</p>
        </div>

        <div className="mt-20 flex items-center justify-center gap-8 text-white/60 text-sm flex-wrap">
          {["AI編集指示", "FCPXML", "MP4出力", "SRT字幕", "FCP / Premiere / DaVinci"].map((label) => (
            <div key={label} className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-cyan-400" />
              {label}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Features() {
  const t = useTranslations("features");
  const icons = [Scissors, FileText, BookOpen, Film, Captions, Zap];
  const keys = ["silence", "transcript", "chapters", "fcpxml", "mp4", "async"] as const;

  return (
    <section id="features" className="py-24 px-4 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-gray-900 mb-4">{t("title")}</h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto">{t("subtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {keys.map((key, i) => {
            const Icon = icons[i];
            return (
              <div
                key={key}
                className="p-6 rounded-2xl border border-purple-100 hover:border-purple-300 hover:shadow-lg hover:shadow-purple-100 transition-all group bg-gradient-to-br from-white to-purple-50"
              >
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-bold text-gray-900 mb-2 text-lg">{t(`items.${key}.title`)}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{t(`items.${key}.description`)}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const t = useTranslations("howItWorks");
  const stepKeys = ["upload", "analyze", "download"] as const;
  const colors = [
    "from-purple-500 to-violet-600",
    "from-violet-500 to-blue-600",
    "from-blue-500 to-cyan-600",
  ];

  return (
    <section className="py-24 px-4 bg-gradient-to-br from-gray-950 to-purple-950">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-white mb-4">{t("title")}</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {stepKeys.map((key, i) => (
            <div key={key} className="text-center">
              <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br ${colors[i]} flex items-center justify-center text-white font-black text-xl shadow-xl`}>
                {t(`steps.${key}.step`)}
              </div>
              <h3 className="font-bold text-white text-xl mb-3">{t(`steps.${key}.title`)}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{t(`steps.${key}.description`)}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const t = useTranslations("pricing");
  const locale = useLocale();
  const planKeys = ["free", "pro", "creator", "studio"] as const;

  return (
    <section id="pricing" className="py-24 px-4 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-black text-gray-900 mb-4">{t("title")}</h2>
          <p className="text-gray-500 text-lg">{t("subtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {planKeys.map((key) => {
            const isHighlighted = key === "pro";
            const features = t.raw(`plans.${key}.features`) as string[];

            return (
              <div
                key={key}
                className={`rounded-2xl p-6 border-2 transition-all relative ${
                  isHighlighted
                    ? "border-purple-500 bg-gradient-to-br from-purple-600 to-blue-600 text-white shadow-xl shadow-purple-200"
                    : "border-gray-200 bg-white hover:border-purple-200 hover:shadow-lg"
                }`}
              >
                {isHighlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-amber-400 text-amber-900 text-xs font-bold rounded-full">
                    {t(`plans.${key}.badge`)}
                  </span>
                )}

                <div className="mb-4">
                  <h3 className={`font-black text-xl mb-1 ${isHighlighted ? "text-white" : "text-gray-900"}`}>
                    {t(`plans.${key}.name`)}
                  </h3>
                  <p className={`text-xs mb-3 ${isHighlighted ? "text-white/80" : "text-gray-400"}`}>
                    {t(`plans.${key}.description`)}
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className={`text-3xl font-black ${isHighlighted ? "text-white" : "text-gray-900"}`}>
                      {t(`plans.${key}.price`)}
                    </span>
                    <span className={`text-sm ${isHighlighted ? "text-white/70" : "text-gray-400"}`}>
                      /{t(`plans.${key}.period`)}
                    </span>
                  </div>
                </div>

                <ul className="space-y-2 mb-6">
                  {features.map((f: string) => (
                    <li key={f} className={`flex items-start gap-2 text-sm ${isHighlighted ? "text-white/90" : "text-gray-600"}`}>
                      <CheckCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isHighlighted ? "text-cyan-300" : "text-purple-500"}`} />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href={`/${locale}/signup`}
                  className={`block text-center py-3 rounded-xl font-semibold text-sm transition-all ${
                    isHighlighted
                      ? "bg-white text-purple-700 hover:bg-purple-50"
                      : "bg-purple-600 text-white hover:bg-purple-700"
                  }`}
                >
                  {t(`plans.${key}.cta`)}
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  const t = useTranslations("cta");
  const locale = useLocale();

  return (
    <section className="py-24 px-4 bg-gradient-to-r from-purple-600 via-violet-600 to-blue-600">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-4xl font-black text-white mb-4">{t("title")}</h2>
        <p className="text-white/80 text-lg mb-10">{t("description")}</p>
        <Link
          href={`/${locale}/signup`}
          className="inline-flex items-center gap-2 px-10 py-4 bg-white text-purple-700 font-bold rounded-xl hover:bg-purple-50 transition-all shadow-xl text-lg"
        >
          {t("button")} <ArrowRight className="w-5 h-5" />
        </Link>
      </div>
    </section>
  );
}

export default function HomePage() {
  return (
    <main>
      <Header />
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing />
      <CTA />
      <Footer />
    </main>
  );
}
