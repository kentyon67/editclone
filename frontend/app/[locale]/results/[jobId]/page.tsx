"use client";
import { useTranslations, useLocale } from "next-intl";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  Download, Copy, Check, FileVideo, Captions, BookOpen,
  FileText, Loader2, CheckCircle, XCircle, ArrowLeft
} from "lucide-react";
import Header from "@/components/Header";
import { getJobStatus, getDownloadUrl, JobStatusResponse } from "@/lib/api";

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

  return (
    <div>
      <div className="text-center mb-10">
        <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-green-400 to-emerald-600 rounded-2xl flex items-center justify-center shadow-xl">
          <CheckCircle className="w-10 h-10 text-white" />
        </div>
        <h2 className="text-2xl font-black text-gray-900 mb-2">{t("title")}</h2>
        <p className="text-gray-500">{t("subtitle")}</p>
      </div>

      <a
        href={downloadUrl}
        download
        className="flex items-center justify-center gap-3 w-full py-4 mb-6 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 transition-opacity text-lg shadow-lg shadow-purple-200"
      >
        <Download className="w-5 h-5" />
        {t("downloadAll")}
      </a>

      <div className="space-y-4">
        <div className="bg-white rounded-2xl p-5 border border-purple-100">
          <div className="flex items-center gap-3 mb-2">
            <FileVideo className="w-5 h-5 text-purple-500" />
            <h3 className="font-bold text-gray-900">{t("fcpxml.title")}</h3>
          </div>
          <p className="text-sm text-gray-500 mb-1">{t("fcpxml.description")}</p>
          <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">{t("fcpxml.note")}</p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-purple-100">
          <div className="flex items-center gap-3 mb-2">
            <Captions className="w-5 h-5 text-blue-500" />
            <h3 className="font-bold text-gray-900">{t("srt.title")}</h3>
          </div>
          <p className="text-sm text-gray-500">{t("srt.description")}</p>
        </div>

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
