"use client";
import { useTranslations, useLocale } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Film, Globe } from "lucide-react";

export default function Header({ isLoggedIn = false }: { isLoggedIn?: boolean }) {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  function toggleLocale() {
    const next = locale === "ja" ? "en" : "ja";
    const stripped = pathname.replace(`/${locale}`, "") || "/";
    router.push(`/${next}${stripped}`);
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-purple-100">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href={`/${locale}`} className="flex items-center gap-2 font-bold text-xl text-purple-700">
          <Film className="w-6 h-6" />
          EditClone
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-gray-600">
          <a href={`/${locale}#features`} className="hover:text-purple-600 transition-colors">{t("features")}</a>
          <a href={`/${locale}#pricing`} className="hover:text-purple-600 transition-colors">{t("pricing")}</a>
        </nav>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleLocale}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-purple-600 transition-colors"
          >
            <Globe className="w-4 h-4" />
            {locale === "ja" ? "EN" : "JA"}
          </button>

          {isLoggedIn ? (
            <>
              <Link href={`/${locale}/dashboard`} className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
                {t("dashboard")}
              </Link>
              <Link href={`/${locale}/styles`} className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
                {t("styles")}
              </Link>
              <Link href={`/${locale}/account`} className="text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors">
                {t("account")}
              </Link>
            </>
          ) : (
            <>
              <Link href={`/${locale}/login`} className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
                {t("login")}
              </Link>
              <Link href={`/${locale}/signup`} className="text-sm bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-lg hover:opacity-90 transition-opacity font-medium">
                {t("signup")}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
