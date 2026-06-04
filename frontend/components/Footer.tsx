import { useTranslations, useLocale } from "next-intl";
import { Film } from "lucide-react";

export default function Footer() {
  const t = useTranslations("footer");
  const locale = useLocale();

  return (
    <footer className="bg-gray-950 text-gray-400 py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 text-white font-bold text-lg mb-3">
              <Film className="w-5 h-5 text-purple-400" />
              EditClone
            </div>
            <p className="text-sm text-gray-500">{t("tagline")}</p>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">{t("links.product")}</h4>
            <ul className="space-y-2 text-sm">
              <li><a href={`/${locale}#features`} className="hover:text-purple-400 transition-colors">{t("links.features")}</a></li>
              <li><a href={`/${locale}#pricing`} className="hover:text-purple-400 transition-colors">{t("links.pricing")}</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">{t("links.company")}</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="hover:text-purple-400 transition-colors">{t("links.about")}</a></li>
              <li><a href="mailto:hello@editclone.app" className="hover:text-purple-400 transition-colors">{t("links.contact")}</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-3 text-sm">{t("links.legal")}</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="hover:text-purple-400 transition-colors">{t("links.privacy")}</a></li>
              <li><a href="#" className="hover:text-purple-400 transition-colors">{t("links.terms")}</a></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-600">
          {t("copyright")}
        </div>
      </div>
    </footer>
  );
}
