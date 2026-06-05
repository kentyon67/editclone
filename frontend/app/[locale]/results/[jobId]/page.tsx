"use client";
import { useTranslations, useLocale } from "next-intl";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  Download, Copy, Check, Captions, BookOpen,
  FileText, Loader2, CheckCircle, XCircle, ArrowLeft, Film,
  Share2, Clapperboard, MonitorPlay
} from "lucide-react";
import Header from "@/components/Header";
import { getJobStatus, getDownloadUrl, getMp4Url, JobStatusResponse } from "@/lib/api";
import {
  getPluginMode, NLE_LABELS, importToFCP, importToPremiere, importToDaVinci, PluginNLE
} from "@/lib/plugin";

function ProcessingView({ progress }: { progress: string }) {
  const t = useTranslations("processing");
  const steps = ["uploading", "transcribing", "detecting", "generating", "packaging"] as const;

  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-xl">
        <Loader2 className="w-10 h-10 text-white animate-spin" />
      </div>
      <h2 className="text-2xl font-black text-gray-900 mb-2">{t("title")}</h2>
      <p className="text-gray-500 mb-10">{t("subtitle")}</p>

      <div className="max-w-sm mx-auto space-y-3">
        {steps.map((step) => {
          const label = t(`steps.${step}`);
          const active = progress.includes(label.slice(0, 4));
          return (
            <div key={step} className={`flex items-center gap-3 p-3 rounded-xl ${active ? "bg-purple-50 border border-purple-200" : "opacity-40"}`}>
              <div className={`w-2 h-2 rounded-full ${active ? "bg-purple-500 animate-pulse" : "bg-gray-300"}`} />
              <span className="text-sm text-gray-700">{label}</span>
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

function ResultsView({ job }: { job: JobStatusResponse }) {
  const t = useTranslations("results");
  const locale = useLocale();
  const result = job.result!;
  const downloadUrl = getDownloadUrl(job.job_id);
  const [sharing, setSharing] = useState(false);
  const [pluginNLE, setPluginNLE] = useState<PluginNLE>(null);

  useEffect(() => {
    setPluginNLE(getPluginMode());
  }, []);

  async function handleSaveMp4() {
    const mp4Url = getMp4Url(job.job_id);
    setSharing(true);
    try {
      const res = await fetch(mp4Url);
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
              const filename = `${job.job_id}_editclone.zip`;
              if (pluginNLE === "fcp") {
                if (!importToFCP(downloadUrl, filename)) {
                  window.open(downloadUrl);
                }
              } else if (pluginNLE === "premiere") {
                importToPremiere(downloadUrl, filename);
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
            <div className="flex items-center gap-3 mb-2">
              <Captions className="w-5 h-5 text-blue-500" />
              <h3 className="font-bold text-gray-900">{t("srt.title")}</h3>
            </div>
            <p className="text-sm text-gray-500">{t("srt.description")}</p>
          </div>
        )}
      </div>

      <div className="mt-8 text-center">
        <Link
          href={`/${locale}/upload`}
          className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          {t("newVideo")}
        </Link>
      </div>
    </div>
  );
}

export default function ResultsPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
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
        setFatalError("ジョブの取得に失敗しました");
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
    </div>
  );
}
