"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload, Film, Settings, Loader2, ChevronDown } from "lucide-react";
import Header from "@/components/Header";
import { uploadVideo, startProcessing } from "@/lib/api";

export default function UploadPage() {
  const t = useTranslations("upload");
  const locale = useLocale();
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [noiseDb, setNoiseDb] = useState(-30);
  const [minDuration, setMinDuration] = useState(0.5);
  const [showSettings, setShowSettings] = useState(false);
  const [status, setStatus] = useState<"idle" | "uploading" | "processing">("idle");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");

    try {
      setStatus("uploading");
      const uploaded = await uploadVideo(file);

      setStatus("processing");
      const job = await startProcessing(uploaded.video_id, {
        noise_db: noiseDb,
        min_duration: minDuration,
      });

      router.push(`/${locale}/results/${job.job_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error occurred");
      setStatus("idle");
    }
  }

  const isLoading = status !== "idle";

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        <h1 className="text-3xl font-black text-gray-900 mb-8">{t("title")}</h1>

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
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
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
                  {t("noiseDb")}: <span className="text-purple-600 font-bold">{noiseDb} dB</span>
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
                  <span>-60 dB（敏感）</span>
                  <span>-10 dB（鈍感）</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("minDuration")}: <span className="text-purple-600 font-bold">{minDuration}s</span>
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
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">{error}</div>
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
    </div>
  );
}
