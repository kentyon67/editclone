"use client";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  ArrowLeft, Layers, Wifi, AlertTriangle, Globe, Puzzle,
  RotateCcw, Film, X, Clock, Loader2, ChevronRight,
  Scissors, MessageSquare,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { getProject, reExportProject, type Project, type ProjectRevision } from "@/lib/api";
import { useRouter } from "next/navigation";

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  return d.toLocaleString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function SyncBadge({ status }: { status: Project["sync_status"] }) {
  const t = useTranslations("projects");
  if (status === "synced") return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">
      <Wifi className="w-4 h-4" /> {t("syncSynced")}
    </span>
  );
  if (status === "conflict") return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">
      <AlertTriangle className="w-4 h-4" /> {t("syncConflict")}
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 bg-gray-100 border border-gray-200 px-3 py-1 rounded-full">
      <Globe className="w-4 h-4" /> {t("syncLocal")}
    </span>
  );
}

function RevisionCard({ revision, locale }: { revision: ProjectRevision; locale: string }) {
  const t = useTranslations("projects");
  const meta = revision.metadata as Record<string, unknown> | null;
  const cutCount = meta?.cut_count as number | null;
  const hasPrompt = !!(meta?.prompt as string | null);

  return (
    <div className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-gray-100">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
        revision.source === "plugin"
          ? "bg-purple-100 text-purple-600"
          : "bg-blue-100 text-blue-600"
      }`}>
        {revision.source === "plugin" ? <Puzzle className="w-4 h-4" /> : <Globe className="w-4 h-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-gray-900 text-sm">
            {t("revision", { number: revision.revision_number })}
          </span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            revision.source === "plugin"
              ? "bg-purple-50 text-purple-700"
              : "bg-blue-50 text-blue-700"
          }`}>
            {revision.source === "plugin" ? t("sourcePlugin") : t("sourceWeb")}
          </span>
          {cutCount !== null && cutCount !== undefined && (
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Scissors className="w-3 h-3" />
              {t("cutCount", { count: cutCount })}
            </span>
          )}
          {hasPrompt && (
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" />
              {t("hasPrompt")}
            </span>
          )}
        </div>
        {revision.notes && (
          <p className="text-sm text-gray-500 mt-0.5 truncate">{revision.notes}</p>
        )}
        <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatDate(revision.created_at, locale)}
        </p>
      </div>
    </div>
  );
}

function ReExportModal({
  onClose,
  onStart,
  originalPrompt,
}: {
  onClose: () => void;
  onStart: (prompt: string) => void;
  originalPrompt: string;
}) {
  const t = useTranslations("projects");
  const [prompt, setPrompt] = useState(originalPrompt);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">{t("reExportTitle")}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{t("reExportDesc")}</p>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("reExportPromptLabel")}
        </label>
        <textarea
          className="w-full border border-gray-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 resize-none"
          rows={3}
          placeholder={t("reExportPromptPlaceholder")}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div className="flex gap-3 mt-5">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-200 text-gray-700 rounded-xl py-2.5 font-medium text-sm hover:bg-gray-50 transition-colors"
          >
            {t("reExportCancel")}
          </button>
          <button
            onClick={() => onStart(prompt)}
            className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl py-2.5 font-medium text-sm hover:opacity-90 transition-opacity"
          >
            {t("reExportStart")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: projectId } = use(params);
  const locale = useLocale();
  const t = useTranslations("projects");
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [showReExportModal, setShowReExportModal] = useState(false);
  const [reExporting, setReExporting] = useState(false);

  useEffect(() => {
    getProject(projectId).then((p) => {
      setProject(p);
      setLoading(false);
    });
  }, [projectId]);

  const sortedRevisions = [...(project?.project_revisions ?? [])].sort(
    (a, b) => b.revision_number - a.revision_number,
  );

  const originalPrompt = (() => {
    const webRevision = project?.project_revisions?.find((r) => r.source === "web");
    const meta = webRevision?.metadata as Record<string, unknown> | null;
    return (meta?.prompt as string) ?? "";
  })();

  async function handleReExport(prompt: string) {
    if (!project) return;
    setReExporting(true);
    setShowReExportModal(false);
    try {
      const { job_id } = await reExportProject(project.id, prompt || undefined);
      router.push(`/${locale}/results/${job_id}`);
    } catch {
      setReExporting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header isLoggedIn />
        <main className="pt-24 pb-16 px-4 max-w-3xl mx-auto text-center">
          <p className="text-gray-500">{t("notFound")}</p>
          <Link href={`/${locale}/dashboard`} className="mt-4 inline-flex items-center gap-2 text-purple-600 hover:underline text-sm">
            <ArrowLeft className="w-4 h-4" /> {t("back")}
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      {showReExportModal && (
        <ReExportModal
          onClose={() => setShowReExportModal(false)}
          onStart={handleReExport}
          originalPrompt={originalPrompt}
        />
      )}

      <main className="pt-24 pb-16 px-4 max-w-3xl mx-auto">
        {/* Back */}
        <Link
          href={`/${locale}/dashboard`}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-purple-600 transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> {t("back")}
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center flex-shrink-0">
              <Layers className="w-6 h-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-black text-gray-900 truncate">{project.name}</h1>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <SyncBadge status={project.sync_status} />
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(project.created_at, locale)}
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowReExportModal(true)}
            disabled={reExporting}
            className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2.5 rounded-xl font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-60 flex-shrink-0"
          >
            {reExporting ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> {t("reExporting")}</>
            ) : (
              <><RotateCcw className="w-4 h-4" /> {t("reExport")}</>
            )}
          </button>
        </div>

        {/* Conflict warning */}
        {project.sync_status === "conflict" && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-700">{t("syncConflictHelp")}</p>
          </div>
        )}

        {/* Original job link */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">{t("originalJob")}</p>
          <Link
            href={`/${locale}/results/${project.source_job_id}`}
            className="flex items-center gap-3 group"
          >
            <div className="w-9 h-9 bg-gradient-to-br from-purple-100 to-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
              <Film className="w-4 h-4 text-purple-500" />
            </div>
            <span className="text-sm font-medium text-gray-700 group-hover:text-purple-600 transition-colors truncate flex-1">
              {t("viewJob")}
            </span>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-purple-400 transition-colors flex-shrink-0" />
          </Link>
        </div>

        {/* Revisions */}
        <div className="bg-white rounded-2xl border border-gray-100 p-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">{t("revisions")}</p>
          {sortedRevisions.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">{t("noRevisions")}</p>
          ) : (
            <div className="space-y-2">
              {sortedRevisions.map((rev) => (
                <RevisionCard key={rev.id} revision={rev} locale={locale} />
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
