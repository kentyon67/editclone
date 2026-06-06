"use client";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Layers, ArrowLeft, Loader2, Film, ChevronRight,
  Wifi, AlertTriangle, Clock,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { listProjects, type Project } from "@/lib/api";

function formatDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric", month: "short", day: "numeric",
  });
}

function SyncBadge({ status }: { status: Project["sync_status"] }) {
  const t = useTranslations("projects");
  if (status === "synced") return (
    <span className="flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full font-medium">
      <Wifi className="w-3 h-3" /> {t("syncSynced")}
    </span>
  );
  if (status === "conflict") return (
    <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
      <AlertTriangle className="w-3 h-3" /> {t("syncConflict")}
    </span>
  );
  return (
    <span className="flex items-center gap-1 text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full font-medium">
      {t("syncLocal")}
    </span>
  );
}

export default function ProjectsListPage() {
  const t = useTranslations("projects");
  const locale = useLocale();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listProjects()
      .then(({ projects: ps }) => setProjects(ps))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />
      <main className="pt-24 pb-16 px-4 max-w-3xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/${locale}/dashboard`}
            className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-purple-600 transition-colors mb-4"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {t("back")}
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-gray-900">{t("listTitle")}</h1>
              <p className="text-sm text-gray-500">{t("listSubtitle")}</p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        )}

        {!loading && projects.length === 0 && (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
            <Layers className="w-12 h-12 mx-auto mb-3 text-gray-200" />
            <p className="font-semibold text-gray-500">{t("listEmpty")}</p>
            <p className="text-sm text-gray-400 mt-1">{t("listEmptySub")}</p>
            <Link
              href={`/${locale}/upload`}
              className="inline-flex items-center gap-2 mt-6 px-5 py-2.5 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors text-sm"
            >
              {t("listEmptySub")}
            </Link>
          </div>
        )}

        {!loading && projects.length > 0 && (
          <div className="space-y-2">
            {projects.map((project) => {
              const revCount = project.project_revisions?.length ?? 0;
              const latestRev = project.project_revisions?.sort(
                (a, b) => b.revision_number - a.revision_number
              )[0];
              const cutCount = latestRev?.metadata
                ? (latestRev.metadata as Record<string, unknown>).cut_count as number | undefined
                : undefined;

              return (
                <Link
                  key={project.id}
                  href={`/${locale}/projects/${project.id}`}
                  className="flex items-center justify-between gap-4 bg-white rounded-2xl border border-gray-100 hover:border-purple-200 hover:shadow-md transition-all p-4 group"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center flex-shrink-0">
                      <Film className="w-5 h-5 text-purple-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 truncate text-sm">{project.name}</p>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="flex items-center gap-1 text-xs text-gray-400">
                          <Clock className="w-3 h-3" />
                          {formatDate(project.created_at, locale)}
                        </span>
                        {revCount > 0 && (
                          <span className="text-xs text-gray-400">
                            Rev. {revCount}
                          </span>
                        )}
                        {cutCount !== undefined && (
                          <span className="text-xs text-gray-400">
                            {t("cutCount", { count: cutCount })}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <SyncBadge status={project.sync_status} />
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-purple-400 transition-colors" />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
