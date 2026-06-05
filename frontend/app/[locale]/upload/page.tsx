"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Upload, Film, Settings, Loader2, ChevronDown, AlertTriangle, ArrowUpRight, Sparkles } from "lucide-react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { uploadVideo, startProcessing, getActiveStyleProfile, ApiError, type StyleProfile } from "@/lib/api";

export default function UploadPage() {
  const t = useTranslations("upload");
  const locale = useLocale();
  const router = useRouter();

  const [activeProfile, setActiveProfile] = useState<StyleProfile | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [noiseDb, setNoiseDb] = useState(-30);
  const [minDuration, setMinDuration] = useState(0.5);
  const [showSettings, setShowSettings] = useState(false);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing">("idle");
  const [error, setError] = useState("");
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getActiveStyleProfile().then(({ profile }) => {
      if (profile) {
        setActiveProfile(profile);
        setNoiseDb(profile.noise_db);
        setMinDuration(profile.min_silence_seconds);
        if (profile.default_prompt) setPrompt(profile.default_prompt);
      }
    }).catch(() => {});
  }, []);

  function readVideoDuration(f: File) {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      setVideoDuration(video.duration);
      URL.revokeObjectURL(video.src);
    };
    video.onerror = () => setVideoDuration(null);
    video.src = URL.createObjectURL(f);
  }

  function selectFile(f: File) {
    setFile(f);
    setVideoDuration(null);
    readVideoDuration(f);
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) selectFile(dropped);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setErrorCode(null);

    try {
      setStatus("uploading");
      const uploaded = await uploadVideo(file);

      setStatus("processing");
      const job = await startProcessing(uploaded.video_id, {
        noise_db: noiseDb,
        min_duration: minDuration,
        prompt: prompt.trim() || undefined,
      });

      router.push(`/${locale}/results/${job.job_id}`);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
        setErrorCode(err.code ?? null);
      } else {
        setError(err instanceof Error ? err.message : "Error occurred");
      }
      setStatus("idle");
    }
  }

  const isLoading = status !== "idle";

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        <div className="flex items-start justify-between gap-4 mb-8">
          <h1 className="text-3xl font-black text-gray-900">{t("title")}</h1>
          {activeProfile && (
            <Link
              href={`/${locale}/styles`}
              className="flex items-center gap-1.5 text-xs bg-purple-50 border border-purple-200 text-purple-700 px-3 py-1.5 rounded-full font-medium hover:bg-purple-100 transition-colors flex-shrink-0"
            >
              <Sparkles className="w-3 h-3" />
              {activeProfile.name}
            </Link>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed transition-all py-20 flex flex-col items-center gap-4 ${
              dragging
                ? "border-purple-500 bg-purple-100"
                : file
                ? "border-green-400 bg-green-50"
                : "border-purple-200 bg-white hover:border-purple-400 hover:bg-purple-50"
            }`}
          >
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${file ? "bg-green-500" : "bg-gradient-to-br from-purple-500 to-blue-600"}`}>
              {file ? <Film className="w-8 h-8 text-white" /> : <Upload className="w-8 h-8 text-white" />}
            </div>
            {file ? (
              <>
                <p className="font-bold text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                {videoDuration !== null && (
                  <p className="text-sm text-purple-600 font-medium">
                    {t("duration")}: {Math.floor(videoDuration / 60)}{t("durationUnit")}{" "}
                    {Math.round(videoDuration % 60)}{t("durationSeconds")}
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="font-bold text-gray-700">{t("dropzone")}</p>
                <p className="text-sm text-gray-400">
                  {t("dropzoneOr")}{" "}
                  <span className="text-purple-600 underline">{t("browse")}</span>
                </p>
                <p className="text-xs text-gray-300">{t("formats")}</p>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".mp4,.mov,.m4v"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) selectFile(f); }}
            />
          </div>

          {/* AI editing prompt */}
          <div className="bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <label className="text-sm font-semibold text-purple-900">
                {t("promptLabel")}
              </label>
              <span className="text-xs text-purple-400 font-normal">{t("promptOptional")}</span>
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t("promptPlaceholder")}
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 text-sm bg-white border border-purple-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-400 placeholder-gray-300 text-gray-700"
            />
            <p className="mt-1 text-xs text-purple-400">{t("promptHint")}</p>
          </div>

          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-purple-600 transition-colors"
          >
            <Settings className="w-4 h-4" />
            {t("settings")}
            <ChevronDown className={`w-4 h-4 transition-transform ${showSettings ? "rotate-180" : ""}`} />
          </button>

          {showSettings && (
            <div className="bg-white rounded-2xl p-5 border border-gray-200 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("noiseDb")}
                </label>
                <input
                  type="range"
                  min="-60"
                  max="-10"
                  value={noiseDb}
                  onChange={(e) => setNoiseDb(Number(e.target.value))}
                  className="w-full accent-purple-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>敏感（小さな無音もカット）</span>
                  <span>鈍感（大きな無音のみ）</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("minDuration")}: <span className="text-purple-600 font-bold">{minDuration}秒以上</span>
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="3"
                  step="0.1"
                  value={minDuration}
                  onChange={(e) => setMinDuration(Number(e.target.value))}
                  className="w-full accent-purple-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0.1秒〜</span>
                  <span>〜3秒</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className={`p-4 rounded-xl border text-sm ${
              errorCode === "LIMIT_EXCEEDED" || errorCode === "DURATION_EXCEEDED"
                ? "bg-amber-50 border-amber-200 text-amber-800"
                : "bg-red-50 border-red-200 text-red-600"
            }`}>
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p>{error}</p>
                  {(errorCode === "LIMIT_EXCEEDED" || errorCode === "DURATION_EXCEEDED") && (
                    <Link
                      href={`/${locale}/pricing`}
                      className="inline-flex items-center gap-1 mt-2 font-semibold text-purple-700 hover:text-purple-900"
                    >
                      プランをアップグレード <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={!file || isLoading}
            className="w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 text-lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {status === "uploading" ? t("uploading") : t("processing")}
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                {t("submit")}
              </>
            )}
          </button>
        </form>
      </main>
      <Footer />
    </div>
  );
}
