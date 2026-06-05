"use client";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Upload, Film, ChevronRight, Loader2, CheckCircle, XCircle,
  Clock, Layers, Wifi, AlertTriangle,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  getUserUsage, getUserJobs, listProjects,
  type UsageResponse, type UserJob, type Project,
} from "@/lib/api";
import { setPluginMode, type PluginNLE } from "@/lib/plugin";

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(locale === "ja" ? "ja-JP" : "en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function StatusBadge({ status }: { status: UserJob["status"] }) {
  const t = useTranslations("dashboard");
  if (status === "completed") return (
    <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
      <CheckCircle className="w-3 h-3" /> {t("statusCompleted")}
    </span>
  );
  if (status === "failed") return (
    <span className="flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
      <XCircle className="w-3 h-3" /> {t("statusFailed")}
    </span>
  );
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full">
      <Loader2 className="w-3 h-3 animate-spin" /> {t("statusProcessing")}
    </span>
  );
}

function SyncBadge({ status }: { status: Project["sync_status"] }) {
  const t = useTranslations("dashboard");
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
  return null;
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale();

  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [jobs, setJobs] = useState<UserJob[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const plugin = params.get("plugin") as PluginNLE;
    if (plugin && ["fcp", "premiere", "davinci"].includes(plugin)) {
      setPluginMode(plugin);
    }

    Promise.allSettled([
      getUserUsage().then(setUsage).catch(() =>
        setUsage({ plan: "free", used: 0, limit: 3, remaining: 3, max_duration_seconds: 180 })
      ),
      getUserJobs().then((d) => setJobs(d.jobs)).catch(() => {}),
      listProjects().then((d) => setProjects(d.projects)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const plan = usage?.plan ?? "free";
  const used = usage?.used ?? 0;
  const limit = usage?.limit ?? null;
  const remaining = usage?.remaining ?? null;
  const displayRemaining = remaining === null ? "∞" : remaining;
  const displayLimit = limit === null ? "∞" : limit;

  const nextPlanLabels: Record<string, string> = {
    free: t("nextPlanFree"),
    pro: t("nextPlanPro"),
    creator: t("nextPlanCreator"),
  };
  const upgradeLabel = nextPlanLabels[plan];

  // jobId → project のマップ（sync バッジ表示に使用）
  const jobProjectMap = useMemo(() => {
    const map: Record<string, Project> = {};
    for (const p of projects) {
      map[p.source_job_id] = p;
    }
    return map;
  }, [projects]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-black text-gray-900">{t("title")}</h1>
          <p className="text-gray-500 mt-1">{t("subtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* プランカード */}
          <div className="bg-white rounded-2xl p-5 border border-purple-100 shadow-sm">
            <p className="text-sm text-gray-500 mb-1">{t("plan")}</p>
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
            ) : (
              <p className="text-2xl font-black text-purple-600 capitalize">{plan}</p>
            )}
          </div>

          {/* 残り本数カード */}
          <div className="bg-white rounded-2xl p-5 border border-purple-100 shadow-sm">
            <p className="text-sm text-gray-500 mb-1">{t("remaining")}</p>
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            ) : (
              <div>
                <p className="text-2xl font-black text-gray-900">
                  {displayRemaining}{" "}
                  <span className="text-sm font-normal text-gray-400">/ {displayLimit}</span>
                </p>
                {limit !== null && (
                  <div className="mt-2 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all"
                      style={{ width: `${Math.min(100, (used / limit) * 100)}%` }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* プロジェクト数 or アップグレードカード */}
          {upgradeLabel ? (
            <div className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-2xl p-5 flex items-center justify-between">
              <div>
                <p className="text-sm text-white/70 mb-1">{t("upgrade")}</p>
                <p className="text-white font-bold">{upgradeLabel}</p>
              </div>
              <Link
                href={`/${locale}/pricing`}
                className="bg-white/20 hover:bg-white/30 text-white rounded-xl p-2 transition-colors"
              >
                <ChevronRight className="w-5 h-5" />
              </Link>
            </div>
          ) : (
            <div className="bg-white rounded-2xl p-5 border border-purple-100 shadow-sm">
              <p className="text-sm text-gray-500 mb-1">{t("projects")}</p>
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              ) : (
                <div className="flex items-end gap-2">
                  <p className="text-2xl font-black text-gray-900">{t("projectCount", { count: projects.length })}</p>
                  <Layers className="w-5 h-5 text-purple-400 mb-0.5" />
                </div>
              )}
              <p className="text-xs text-gray-400 mt-1">{t("studioUnlimited")}</p>
            </div>
          )}
        </div>

        {/* アップロードボタン */}
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

        {/* ジョブ履歴 */}
        {jobs.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-3">{t("history")}</h2>
            <div className="space-y-2">
              {jobs.map((job) => {
                const project = jobProjectMap[job.job_id];
                return (
                  <Link
                    key={job.job_id}
                    href={`/${locale}/results/${job.job_id}`}
                    className="flex items-center justify-between gap-4 bg-white rounded-2xl border border-gray-100 hover:border-purple-200 hover:shadow-md transition-all p-4 group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center flex-shrink-0">
                        <Film className="w-5 h-5 text-purple-500" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-gray-900 truncate text-sm">
                          {job.video_filename || job.video_id}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <span className="flex items-center gap-1 text-xs text-gray-400">
                            <Clock className="w-3 h-3" />
                            {formatDate(job.created_at, locale)}
                          </span>
                          {job.cut_count !== null && (
                            <span className="text-xs text-gray-400">
                              {t("cutCount", { count: job.cut_count })}
                            </span>
                          )}
                          {job.has_mp4 && (
                            <span className="text-xs text-green-600 font-medium">{t("hasMp4")}</span>
                          )}
                          {project && <SyncBadge status={project.sync_status} />}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <StatusBadge status={job.status} />
                      <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-purple-400 transition-colors" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {!loading && jobs.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            <Film className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">{t("noVideos")}</p>
            <p className="text-sm">{t("noVideosSub")}</p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
