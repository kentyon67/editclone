"use client";
import { useTranslations, useLocale } from "next-intl";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  Download, Copy, Check, Captions, BookOpen,
  FileText, Loader2, CheckCircle, XCircle, ArrowLeft, Film,
  Share2, Clapperboard, MonitorPlay, Scissors, ThumbsUp, ThumbsDown, Minus, Layers
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { getJobStatus, getDownloadUrl, getMp4Url, getActiveStyleProfile, listProjects, API_URL, JobStatusResponse, postFeedback, type Project } from "@/lib/api";
import {
  getPluginMode, NLE_LABELS, importToFCP, importToPremiere, importToDaVinci, PluginNLE
} from "@/lib/plugin";
import { createClient } from "@/lib/supabase";

// バックエンドの progress 文字列からステップインデックスを判定する
function getProgressStepIndex(progress: string): number {
  if (progress.includes("文字起こし") || progress.includes("transcrib")) return 1;
  if (progress.includes("無音") || progress.includes("AI") || progress.includes("silence")) return 2;
  if (
    progress.includes("チャプター") ||
    progress.includes("字幕") ||
    progress.includes("FCPXML") ||
    progress.includes("Premiere") ||
    progress.includes("EDL")
  ) return 3;
  if (
    progress.includes("MP4") ||
    progress.includes("まとめ") ||
    progress.includes("完了") ||
    progress.includes("テロップ")
  ) return 4;
  return 0;
}

function ProcessingView({ progress }: { progress: string }) {
  const t = useTranslations("processing");
  const steps = ["uploading", "transcribing", "detecting", "generating", "packaging"] as const;
  const activeIndex = getProgressStepIndex(progress);

  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-xl">
        <Loader2 className="w-10 h-10 text-white animate-spin" />
      </div>
      <h2 className="text-2xl font-black text-gray-900 mb-2">{t("title")}</h2>
      <p className="text-gray-500 mb-10">{t("subtitle")}</p>

      <div className="max-w-sm mx-auto space-y-3">
        {steps.map((step, i) => {
          const done = i < activeIndex;
          const active = i === activeIndex;
          return (
            <div
              key={step}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
                active
                  ? "bg-purple-50 border border-purple-200"
                  : done
                  ? "opacity-60"
                  : "opacity-30"
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  active ? "bg-purple-500 animate-pulse" : done ? "bg-emerald-400" : "bg-gray-300"
                }`}
              />
              <span className="text-sm text-gray-700">{t(`steps.${step}`)}</span>
            </div>
          );
        })}
      </div>

      {progress && (
        <p className="mt-6 text-sm text-purple-600 font-medium">{progress}</p>
      )}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const t = useTranslations("results.chapters");

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors"
    >
      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      {copied ? t("copied") : t("copy")}
    </button>
  );
}

function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(1);
  return `${m}:${s.padStart(4, "0")}`;
}

function ResultsView({ job }: { job: JobStatusResponse }) {
  const t = useTranslations("results");
  const locale = useLocale();
  const result = job.result!;
  const downloadUrl = getDownloadUrl(job.job_id);
  const [sharing, setSharing] = useState(false);
  const [pluginNLE, setPluginNLE] = useState<PluginNLE>(null);
  const [sessionToken, setSessionToken] = useState<string>("");
  const [feedbackSent, setFeedbackSent] = useState<string | null>(null);
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
  const [linkedProject, setLinkedProject] = useState<Project | null>(null);

  useEffect(() => {
    setPluginNLE(getPluginMode());
    createClient().auth.getSession().then(({ data }) => {
      if (data.session?.access_token) setSessionToken(data.session.access_token);
    });
    getActiveStyleProfile().then(({ profile }) => {
      if (profile) setActiveProfileId(profile.id);
    }).catch(() => {});
    listProjects().then(({ projects }) => {
      const p = projects.find((proj) => proj.source_job_id === job.job_id);
      if (p) setLinkedProject(p);
    }).catch(() => {});
  }, [job.job_id]);

  async function handleSaveMp4() {
    const mp4Url = getMp4Url(job.job_id);
    setSharing(true);
    try {
      const { createClient: _sc } = await import("@/lib/supabase");
      const { data: _sd } = await _sc().auth.getSession();
      const _tok = _sd.session?.access_token;
      const res = await fetch(mp4Url, _tok ? { headers: { Authorization: `Bearer ${_tok}` } } : {});
      const blob = await res.blob();
      const file = new File([blob], "editclone_video.mp4", { type: "video/mp4" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: t("mp4ShareTitle") });
      } else {
        const a = document.createElement("a");
        a.href = mp4Url;
        a.download = "editclone_video.mp4";
        a.click();
      }
    } catch {
      const a = document.createElement("a");
      a.href = getMp4Url(job.job_id);
      a.download = "editclone_video.mp4";
      a.click();
    } finally {
      setSharing(false);
    }
  }

  return (
    <div>
      <div className="text-center mb-10">
        <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-green-400 to-emerald-600 rounded-2xl flex items-center justify-center shadow-xl">
          <CheckCircle className="w-10 h-10 text-white" />
        </div>
        <h2 className="text-2xl font-black text-gray-900 mb-2">{t("title")}</h2>
        <p className="text-gray-500">{t("subtitle")}</p>
      </div>

      {/* Primary: Save finished video */}
      {result.has_mp4 && (
        <div className="mb-4 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Film className="w-5 h-5 text-green-600" />
            <span className="font-bold text-green-900">{t("mp4SectionTitle")}</span>
            {result.has_subtitles && (
              <span className="text-xs bg-green-200 text-green-800 px-2 py-0.5 rounded-full font-medium">
                {t("withTelopp")}
              </span>
            )}
          </div>
          <p className="text-sm text-green-700 mb-4">{t("mp4Description")}</p>
          <button
            onClick={handleSaveMp4}
            disabled={sharing}
            className="w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold rounded-xl hover:opacity-90 transition-opacity text-lg shadow-lg shadow-green-200 disabled:opacity-60"
          >
            {sharing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Share2 className="w-5 h-5" />}
            {t("saveMp4")}
          </button>
          <a
            href={getMp4Url(job.job_id)}
            download
            className="mt-2 w-full flex items-center justify-center gap-2 py-2 text-sm text-green-600 hover:text-green-800 transition-colors"
          >
            <Download className="w-4 h-4" />
            {t("downloadMp4")}
          </a>
        </div>
      )}

      {/* Plugin NLE Import Button */}
      {pluginNLE && (
        <div className="mb-4">
          <button
            onClick={() => {
              if (pluginNLE === "fcp") {
                const sent = importToFCP(job.job_id, sessionToken, API_URL);
                if (!sent) window.open(downloadUrl);
              } else if (pluginNLE === "premiere") {
                importToPremiere(job.job_id, sessionToken, API_URL);
              } else {
                importToDaVinci(downloadUrl);
              }
            }}
            className={`w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r ${NLE_LABELS[pluginNLE].color} text-white font-bold rounded-xl hover:opacity-90 transition-opacity text-lg shadow-lg`}
          >
            <MonitorPlay className="w-5 h-5" />
            {NLE_LABELS[pluginNLE].importLabel}
          </button>
        </div>
      )}

      {/* Secondary: Editing project ZIP */}
      <div className="mb-6 bg-white border border-purple-100 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <Clapperboard className="w-5 h-5 text-purple-600" />
          <span className="font-bold text-gray-900">{t("editingSectionTitle")}</span>
        </div>
        <p className="text-sm text-gray-500 mb-4">{t("editingDescription")}</p>
        <a
          href={downloadUrl}
          download
          className="w-full flex items-center justify-center gap-3 py-3 border-2 border-purple-300 text-purple-700 font-bold rounded-xl hover:bg-purple-50 hover:border-purple-400 transition-colors"
        >
          <Download className="w-5 h-5" />
          {t("downloadAll")}
        </a>
        <p className="mt-2 text-xs text-gray-400 text-center">{t("editingNote")}</p>
      </div>

      {/* Cut summary */}
      {result.cuts && result.cuts.length > 0 && (
        <div className="mb-4 bg-white border border-gray-100 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Scissors className="w-4 h-4 text-purple-500" />
            <span className="font-bold text-gray-900 text-sm">
              {t("cutSummaryTitle")} ({result.cuts.length}{t("cutUnit")})
            </span>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {result.cuts.map((cut: { cut_start: number; cut_end: number; duration: number; reason: string; source?: string }, i: number) => (
              <div key={i} className="flex items-center gap-3 text-xs py-1.5 px-2 rounded-lg hover:bg-gray-50">
                <span className="text-gray-400 w-5 text-right flex-shrink-0">{i + 1}</span>
                <span className="font-mono text-gray-600 flex-shrink-0">
                  {fmtTime(cut.cut_start)} – {fmtTime(cut.cut_end)}
                </span>
                <span className="text-gray-400 flex-shrink-0">({cut.duration.toFixed(1)}s)</span>
                <span className="text-gray-500 truncate">{cut.reason}</span>
                {cut.source === "ai" || cut.source === "ai+silence" ? (
                  <span className="text-purple-500 font-medium flex-shrink-0">AI</span>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info cards */}
      <div className="space-y-4">
        {result.youtube_description && (
          <div className="bg-white rounded-2xl p-5 border border-purple-100">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <BookOpen className="w-5 h-5 text-red-500" />
                <h3 className="font-bold text-gray-900">{t("chapters.title")}</h3>
              </div>
              <CopyButton text={result.youtube_description} />
            </div>
            <p className="text-sm text-gray-500 mb-3">{t("chapters.description")}</p>
            <pre className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 font-mono whitespace-pre-wrap overflow-auto max-h-48">
              {result.youtube_description}
            </pre>
          </div>
        )}

        {result.transcript?.transcript && (
          <div className="bg-white rounded-2xl p-5 border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <FileText className="w-5 h-5 text-gray-400" />
              <h3 className="font-bold text-gray-900">{t("transcript.title")}</h3>
            </div>
            <p className="text-sm text-gray-500 mb-3">{t("transcript.description")}</p>
            <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 max-h-48 overflow-auto leading-relaxed">
              {result.transcript.transcript}
            </div>
          </div>
        )}

        {result.srt && (
          <div className="bg-white rounded-2xl p-5 border border-purple-100">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <Captions className="w-5 h-5 text-blue-500" />
                <h3 className="font-bold text-gray-900">{t("srt.title")}</h3>
              </div>
              <button
                onClick={() => {
                  const blob = new Blob([result.srt], { type: "text/plain;charset=utf-8" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `${job.video_id}.srt`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-colors"
              >
                <Download className="w-4 h-4" />
                {t("downloadSrt")}
              </button>
            </div>
            <p className="text-sm text-gray-500">{t("srt.description")}</p>
          </div>
        )}
      </div>

      {/* フィードバック */}
      <div className="mt-8 bg-white border border-gray-100 rounded-2xl p-5">
        {feedbackSent ? (
          <div className="flex items-center justify-center gap-2 text-emerald-600 font-medium text-sm py-1">
            <CheckCircle className="w-4 h-4" />
            {t("feedback.done")}
          </div>
        ) : (
          <>
            <p className="text-sm font-semibold text-gray-700 text-center mb-3">{t("feedback.title")}</p>
            <div className="flex gap-3 justify-center">
              {(["accept", "partial", "reject"] as const).map((action) => {
                const Icon = action === "accept" ? ThumbsUp : action === "partial" ? Minus : ThumbsDown;
                const label = t(`feedback.${action}`);
                const colors = {
                  accept: "border-emerald-200 text-emerald-700 hover:bg-emerald-50",
                  partial: "border-gray-200 text-gray-600 hover:bg-gray-50",
                  reject: "border-red-200 text-red-600 hover:bg-red-50",
                };
                return (
                  <button
                    key={action}
                    onClick={async () => {
                      await postFeedback({
                        job_id: job.job_id,
                        action,
                        style_profile_id: activeProfileId ?? undefined,
                      }).catch(() => {});
                      setFeedbackSent(action);
                    }}
                    className={`flex items-center gap-2 px-4 py-2 border rounded-xl text-sm font-medium transition-colors ${colors[action]}`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>

      <div className="mt-6 flex items-center justify-center gap-4 flex-wrap">
        <Link
          href={`/${locale}/upload`}
          className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          {t("newVideo")}
        </Link>
        {linkedProject && (
          <Link
            href={`/${locale}/projects/${linkedProject.id}`}
            className="inline-flex items-center gap-2 text-gray-500 hover:text-purple-600 font-medium text-sm border border-gray-200 hover:border-purple-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Layers className="w-4 h-4" />
            {t("viewProject")}
          </Link>
        )}
      </div>
    </div>
  );
}

export default function ResultsPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const t = useTranslations("results");
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [fatalError, setFatalError] = useState("");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const data = await getJobStatus(jobId);
        setJob(data);
        if (data.status === "pending" || data.status === "processing") {
          timer = setTimeout(poll, 2000);
        }
      } catch {
        setFatalError(t("loadError"));
      }
    }

    poll();
    return () => clearTimeout(timer);
  }, [jobId]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />
      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        {fatalError && (
          <div className="text-center py-16">
            <XCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
            <p className="text-red-600 font-medium">{fatalError}</p>
          </div>
        )}
        {!job && !fatalError && (
          <div className="text-center py-16">
            <Loader2 className="w-10 h-10 mx-auto animate-spin text-purple-500" />
          </div>
        )}
        {job?.status === "failed" && (
          <div className="text-center py-16">
            <XCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
            <p className="text-red-600 font-medium">{job.error}</p>
          </div>
        )}
        {(job?.status === "pending" || job?.status === "processing") && (
          <ProcessingView progress={job.progress || ""} />
        )}
        {job?.status === "completed" && <ResultsView job={job} />}
      </main>
      <Footer />
    </div>
  );
}
