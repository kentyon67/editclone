"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Dna, Upload, ArrowLeft, Loader2, Film, CheckCircle2, ChevronRight,
  Scissors, Clock, BarChart2, Mic2, Lightbulb, Gauge, Captions, ZoomIn,
  Shuffle, Type, Volume2, Palette, MapPin, Music, Crop, FileVideo,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  analyzeEditPair, applyDnaToProfile, listStyleProfiles,
  ApiError,
  type EditDnaResult, type StyleProfile,
} from "@/lib/api";

function VideoDropzone({
  label,
  file,
  onFile,
  dropText,
}: {
  label: string;
  file: File | null;
  onFile: (f: File) => void;
  dropText: string;
}) {
  const t = useTranslations("analyze");
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) onFile(f);
    },
    [onFile]
  );

  return (
    <div className="flex-1 min-w-0">
      <label className="block text-sm font-semibold text-gray-700 mb-2">{label}</label>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed transition-all py-8 flex flex-col items-center gap-3 ${
          dragging
            ? "border-purple-500 bg-purple-50"
            : file
            ? "border-green-400 bg-green-50"
            : "border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50/50"
        }`}
      >
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${file ? "bg-green-500" : "bg-gradient-to-br from-purple-500 to-blue-600"}`}>
          <Film className="w-5 h-5 text-white" />
        </div>
        {file ? (
          <>
            <p className="text-sm font-semibold text-gray-800 px-3 text-center truncate max-w-full">{file.name}</p>
            <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
          </>
        ) : (
          <>
            <p className="text-sm font-medium text-gray-600 text-center px-3">{dropText}</p>
            <p className="text-xs text-gray-400">
              {t("formats")}
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.m4v"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
        />
      </div>
    </div>
  );
}

function DnaResultCard({ result }: { result: EditDnaResult }) {
  const t = useTranslations("analyze");

  const removedPct = Math.round(result.removed_ratio * 100);
  const cutLabel =
    result.cuts_per_minute >= 5 ? "テンポ速め" :
    result.cuts_per_minute >= 2 ? "標準" : "ゆったり";

  return (
    <div className="bg-white rounded-2xl border border-purple-200 shadow-sm p-6 space-y-5">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
          <Dna className="w-4 h-4 text-purple-600" />
        </div>
        <h2 className="font-bold text-gray-900">{t("resultTitle")}</h2>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-purple-50 rounded-xl p-3 text-center">
          <Scissors className="w-4 h-4 text-purple-500 mx-auto mb-1" />
          <p className="text-xl font-black text-purple-700">{removedPct}%</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("removedRatio")}</p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3 text-center">
          <Clock className="w-4 h-4 text-blue-500 mx-auto mb-1" />
          <p className="text-xl font-black text-blue-700">{result.removed_seconds}{t("seconds")}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("removedSeconds")}</p>
        </div>
        <div className="bg-green-50 rounded-xl p-3 text-center">
          <BarChart2 className="w-4 h-4 text-green-500 mx-auto mb-1" />
          <p className="text-xl font-black text-green-700">{result.cuts_per_minute}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("cutsPerMin")}</p>
          <p className="text-[10px] text-green-600 font-medium">{cutLabel}</p>
        </div>
        <div className="bg-orange-50 rounded-xl p-3 text-center">
          <Mic2 className="w-4 h-4 text-orange-500 mx-auto mb-1" />
          <p className="text-xl font-black text-orange-700">{result.avg_segment_seconds}{t("secUnit")}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("avgSegment")}</p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between bg-gray-50 rounded-xl px-3 py-2 text-sm">
          <span className="text-gray-500">{t("noiseDb")}</span>
          <span className="font-semibold text-gray-800">{result.detected_noise_db} dB</span>
        </div>
        <div className="bg-purple-50 rounded-xl px-3 py-3">
          <p className="text-xs font-semibold text-purple-700 mb-1">{t("suggestedPrompt")}</p>
          <p className="text-sm text-gray-800 leading-relaxed">{result.suggested_prompt}</p>
        </div>
      </div>

      {result.detected_operations && result.detected_operations.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-2">検出された編集操作</p>
          <div className="flex flex-wrap gap-1.5">
            {result.detected_operations.map((op) => {
              const opMeta: Record<string, { color: string; label: string }> = {
                cut: { color: "bg-purple-100 text-purple-700", label: "カット" },
                trim: { color: "bg-purple-100 text-purple-600", label: "トリム" },
                speed: { color: "bg-blue-100 text-blue-700", label: "速度変更" },
                subtitle: { color: "bg-green-100 text-green-700", label: "字幕" },
                zoom: { color: "bg-cyan-100 text-cyan-700", label: "ズーム" },
                transition: { color: "bg-indigo-100 text-indigo-700", label: "トランジション" },
                text: { color: "bg-yellow-100 text-yellow-700", label: "テキスト" },
                audio: { color: "bg-orange-100 text-orange-700", label: "音量調整" },
                color: { color: "bg-pink-100 text-pink-700", label: "カラー補正" },
                marker: { color: "bg-red-100 text-red-700", label: "マーカー" },
                bgm: { color: "bg-teal-100 text-teal-700", label: "BGM" },
              };
              const meta = opMeta[op] ?? { color: "bg-gray-100 text-gray-700", label: op };
              return (
                <span key={op} className={`text-xs px-2 py-0.5 rounded-full font-medium ${meta.color}`}>
                  {meta.label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {result.style_insights && result.style_insights.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-1.5 mb-1">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
            <p className="text-xs font-semibold text-amber-700">AI スタイル分析</p>
          </div>
          <ul className="space-y-1">
            {result.style_insights.map((insight, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-amber-400 mt-0.5 flex-shrink-0">•</span>
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ApplyToProfile({
  result,
  onApplied,
}: {
  result: EditDnaResult;
  onApplied: () => void;
}) {
  const t = useTranslations("analyze");
  const [profiles, setProfiles] = useState<StyleProfile[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState("");

  async function loadProfiles() {
    setLoading(true);
    const { profiles: ps } = await listStyleProfiles();
    setProfiles(ps);
    if (ps.length > 0) setSelectedId(ps.find((p) => p.is_active)?.id ?? ps[0].id);
    setLoading(false);
  }

  async function handleApply() {
    if (!selectedId) return;
    setApplying(true);
    setError("");
    try {
      await applyDnaToProfile(selectedId, {
        noise_db: result.suggested_noise_db,
        min_silence_seconds: result.suggested_min_silence,
        default_prompt: result.suggested_prompt,
      });
      setApplied(true);
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("applyError"));
    } finally {
      setApplying(false);
    }
  }

  if (applied) {
    return (
      <div className="flex items-center gap-2 py-3 text-green-600 font-semibold text-sm">
        <CheckCircle2 className="w-5 h-5" />
        {t("applied")}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
      <h3 className="font-bold text-gray-900 text-sm">{t("applyToProfile")}</h3>

      {profiles === null ? (
        <button
          onClick={loadProfiles}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-2 text-sm border border-purple-200 text-purple-600 rounded-xl hover:bg-purple-50 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
          {t("profileLabel")}
        </button>
      ) : profiles.length === 0 ? (
        <p className="text-xs text-gray-400">{t("noProfiles")}</p>
      ) : (
        <div className="space-y-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}{p.is_active ? " ★" : ""}
              </option>
            ))}
          </select>
          <button
            onClick={handleApply}
            disabled={applying || !selectedId}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 disabled:opacity-50 text-sm"
          >
            {applying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Dna className="w-4 h-4" />}
            {applying ? t("applying") : t("applyToProfile")}
          </button>
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>
      )}
    </div>
  );
}

export default function AnalyzePage() {
  const t = useTranslations("analyze");
  const locale = useLocale();
  const [before, setBefore] = useState<File | null>(null);
  const [after, setAfter] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<EditDnaResult | null>(null);
  const [error, setError] = useState("");

  async function handleAnalyze() {
    if (!before || !after) return;
    setAnalyzing(true);
    setResult(null);
    setError("");
    try {
      const res = await analyzeEditPair(before, after);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "分析に失敗しました");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/${locale}/styles`}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-purple-600 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" /> {t("back")}
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
              <Dna className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-gray-900">{t("title")}</h1>
              <p className="text-sm text-gray-500">{t("subtitle")}</p>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <div className="flex gap-4">
            <VideoDropzone
              label={t("beforeLabel")}
              file={before}
              onFile={setBefore}
              dropText={t("dropBefore")}
            />
            <VideoDropzone
              label={t("afterLabel")}
              file={after}
              onFile={setAfter}
              dropText={t("dropAfter")}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">
              {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!before || !after || analyzing}
            className="w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 disabled:opacity-50 text-base"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {t("analyzing")}
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                {t("analyzeBtn")}
              </>
            )}
          </button>

          {result && (
            <>
              <DnaResultCard result={result} />
              <ApplyToProfile result={result} onApplied={() => {}} />
            </>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
