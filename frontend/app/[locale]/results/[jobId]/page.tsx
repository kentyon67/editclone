"use client";
import { useTranslations, useLocale } from "next-intl";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  Download, Copy, Check, Captions, BookOpen,
  FileText, Loader2, CheckCircle, XCircle, ArrowLeft, Film,
  Share2, Clapperboard, MonitorPlay, Scissors, ThumbsUp, ThumbsDown, Minus, Layers, Wand2,
  MessageSquare, Send, Sparkles, RefreshCw
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { getJobStatus, getDownloadUrl, getMp4Url, getActiveStyleProfile, listProjects, getBrollSuggestions, refineJob, API_URL, JobStatusResponse, postFeedback, type Project, type BrollSuggestion, type RefineResult } from "@/lib/api";
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

function ProcessingView({ progress, progressPercent }: { progress: string; progressPercent?: number }) {
  const t = useTranslations("processing");
  const steps = ["uploading", "transcribing", "detecting", "generating", "packaging"] as const;
  const activeIndex = getProgressStepIndex(progress);
  const pct = progressPercent ?? 0;

  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-xl">
        <Loader2 className="w-10 h-10 text-white animate-spin" />
      </div>
      <h2 className="text-2xl font-black text-gray-900 mb-2">{t("title")}</h2>
      <p className="text-gray-500 mb-6">{t("subtitle")}</p>

      {/* 進捗バー */}
      <div className="max-w-sm mx-auto mb-8">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>{pct}%</span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${Math.max(3, pct)}%` }}
          />
        </div>
      </div>

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
  const [pluginStatus, setPluginStatus] = useState<{ message: string; success: boolean } | null>(null);
  const [brollSuggestions, setBrollSuggestions] = useState<BrollSuggestion[] | null>(null);
  const [loadingBroll, setLoadingBroll] = useState(false);

  // インタラクティブ編集チャット状態
  type ChatMsg = { role: "user" | "assistant"; content: string; operations?: RefineResult["operations"] };
  const [chatHistory, setChatHistory] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [refinedMp4Url, setRefinedMp4Url] = useState<string | null>(null);

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

    function onPluginStatus(e: Event) {
      const { message, success } = (e as CustomEvent).detail;
      setPluginStatus({ message, success });
      setTimeout(() => setPluginStatus(null), 5000);
    }
    window.addEventListener("editclone-status", onPluginStatus);
    return () => window.removeEventListener("editclone-status", onPluginStatus);
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

      {/* Primary: Finished video — inline player + save */}
      {result.has_mp4 && (
        <div className="mb-4 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-2xl overflow-hidden">
          {/* Inline video player */}
          <div className="bg-black w-full aspect-video">
            <video
              key={getMp4Url(job.job_id)}
              src={getMp4Url(job.job_id)}
              controls
              playsInline
              preload="metadata"
              className="w-full h-full object-contain"
            />
          </div>

          <div className="p-5">
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
        </div>
      )}

      {/* Plugin NLE Import Button */}
      {pluginNLE && (
        <div className="mb-4 space-y-2">
          <button
            onClick={() => {
              setPluginStatus(null);
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
          {pluginStatus && (
            <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium ${
              pluginStatus.success
                ? "bg-green-50 border border-green-200 text-green-700"
                : "bg-red-50 border border-red-200 text-red-600"
            }`}>
              {pluginStatus.success
                ? <CheckCircle className="w-4 h-4 flex-shrink-0" />
                : <XCircle className="w-4 h-4 flex-shrink-0" />}
              {pluginStatus.message}
            </div>
          )}
        </div>
      )}

      {/* ─── インタラクティブ編集チャット ─── */}
      <div className="mb-6 bg-white border border-purple-100 rounded-2xl overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-purple-50 bg-gradient-to-r from-purple-50 to-white">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-bold text-gray-900 text-sm">AI でさらに編集</p>
            <p className="text-xs text-gray-400">プロンプトで自由に調整。動画とFCPXMLが即時更新されます。</p>
          </div>
        </div>

        {/* クイックプリセット */}
        <div className="px-4 py-3 flex flex-wrap gap-2 border-b border-gray-50">
          {[
            "フィラー（えー・あー）を除去",
            "冒頭の挨拶をカット",
            "テンポを1.5倍速に",
            "Shorts向けに1分以内に",
            "静寂を全てカット",
            "字幕を追加",
          ].map((preset) => (
            <button
              key={preset}
              onClick={() => setChatInput(preset)}
              className="text-xs px-2.5 py-1 rounded-full bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-100 transition-colors"
            >
              {preset}
            </button>
          ))}
        </div>

        {/* チャット履歴 */}
        {chatHistory.length > 0 && (
          <div className="px-4 py-3 space-y-3 max-h-64 overflow-y-auto border-b border-gray-50">
            {chatHistory.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
                  msg.role === "user"
                    ? "bg-purple-600 text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"
                }`}>
                  <p className="leading-relaxed">{msg.content}</p>
                  {msg.role === "assistant" && msg.operations && msg.operations.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {msg.operations.filter(op => op.type !== "error").map((op, j) => (
                        <div key={j} className="flex items-center gap-1.5 text-xs text-gray-500">
                          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0" />
                          <span className="font-mono text-purple-600">[{op.type}]</span>
                          <span className="truncate">{op.description}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-2 justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2.5 flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-500" />
                  <span className="text-sm text-gray-500">AIが編集中...</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 更新後プレビュー */}
        {refinedMp4Url && (
          <div className="px-4 py-3 border-b border-gray-50">
            <div className="flex items-center gap-2 mb-2 text-xs text-emerald-600 font-medium">
              <RefreshCw className="w-3.5 h-3.5" />
              編集が適用されました
            </div>
            <video
              key={refinedMp4Url}
              src={refinedMp4Url}
              controls
              playsInline
              className="w-full rounded-xl bg-black aspect-video"
            />
            <div className="flex gap-2 mt-2">
              <a
                href={refinedMp4Url}
                download="editclone_refined.mp4"
                className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors font-medium"
              >
                <Download className="w-3.5 h-3.5" />
                MP4 を保存
              </a>
            </div>
          </div>
        )}

        {/* 入力エリア */}
        <div className="px-4 py-3 flex gap-2">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !chatLoading && chatInput.trim()) {
                e.preventDefault();
                (async () => {
                  const prompt = chatInput.trim();
                  setChatInput("");
                  setChatLoading(true);
                  setChatHistory((h) => [...h, { role: "user", content: prompt }]);
                  try {
                    const res = await refineJob(job.job_id, prompt, true);
                    if (res.mp4_base64) {
                      const blob = new Blob(
                        [Uint8Array.from(atob(res.mp4_base64), (c) => c.charCodeAt(0))],
                        { type: "video/mp4" }
                      );
                      setRefinedMp4Url(URL.createObjectURL(blob));
                    }
                    const opSummary = res.operations
                      .filter((o) => o.type !== "error")
                      .map((o) => o.description || o.type)
                      .join("、") || "操作なし";
                    setChatHistory((h) => [
                      ...h,
                      { role: "assistant", content: opSummary, operations: res.operations },
                    ]);
                  } catch (err) {
                    setChatHistory((h) => [
                      ...h,
                      { role: "assistant", content: `エラー: ${err instanceof Error ? err.message : "不明なエラー"}` },
                    ]);
                  } finally {
                    setChatLoading(false);
                  }
                })();
              }
            }}
            placeholder="例: フィラーを除去して、冒頭の挨拶もカット"
            className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent placeholder:text-gray-400"
            disabled={chatLoading}
          />
          <button
            disabled={chatLoading || !chatInput.trim()}
            onClick={async () => {
              const prompt = chatInput.trim();
              if (!prompt) return;
              setChatInput("");
              setChatLoading(true);
              setChatHistory((h) => [...h, { role: "user", content: prompt }]);
              try {
                const res = await refineJob(job.job_id, prompt, true);
                if (res.mp4_base64) {
                  const blob = new Blob(
                    [Uint8Array.from(atob(res.mp4_base64), (c) => c.charCodeAt(0))],
                    { type: "video/mp4" }
                  );
                  setRefinedMp4Url(URL.createObjectURL(blob));
                }
                const opSummary = res.operations
                  .filter((o) => o.type !== "error")
                  .map((o) => o.description || o.type)
                  .join("、") || "操作なし";
                setChatHistory((h) => [
                  ...h,
                  { role: "assistant", content: opSummary, operations: res.operations },
                ]);
              } catch (err) {
                setChatHistory((h) => [
                  ...h,
                  { role: "assistant", content: `エラー: ${err instanceof Error ? err.message : "不明なエラー"}` },
                ]);
              } finally {
                setChatLoading(false);
              }
            }}
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-200 text-white rounded-xl transition-colors flex items-center gap-1.5 text-sm font-medium"
          >
            {chatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>

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
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <Scissors className="w-4 h-4 text-purple-500" />
              <span className="font-bold text-gray-900 text-sm">
                {t("cutSummaryTitle")} ({result.cuts.length}{t("cutUnit")})
              </span>
            </div>
            {(() => {
              const totalSaved = result.cuts.reduce(
                (sum: number, c: { duration: number }) => sum + (c.duration || 0), 0
              );
              if (totalSaved < 0.5) return null;
              const m = Math.floor(totalSaved / 60);
              const s = Math.round(totalSaved % 60);
              const label = m > 0 ? `${m}分${s}秒` : `${s}秒`;
              return (
                <span className="text-xs font-semibold text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                  -{label} {t("timeSaved")}
                </span>
              );
            })()}
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

      {/* B-roll 提案 */}
      <div className="mt-4 bg-white border border-gray-100 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-blue-500" />
            <span className="font-bold text-gray-900 text-sm">B-roll 提案</span>
          </div>
          {brollSuggestions === null && (
            <button
              onClick={async () => {
                setLoadingBroll(true);
                try {
                  const data = await getBrollSuggestions(job.job_id);
                  setBrollSuggestions(data.suggestions);
                } catch {
                  setBrollSuggestions([]);
                } finally {
                  setLoadingBroll(false);
                }
              }}
              disabled={loadingBroll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loadingBroll ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
              {loadingBroll ? "生成中..." : "AI で提案生成"}
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mb-3">トランスクリプトを分析してB-roll挿入ポイントを提案します。</p>
        {brollSuggestions !== null && brollSuggestions.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-2">提案はありませんでした</p>
        )}
        {brollSuggestions !== null && brollSuggestions.length > 0 && (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {brollSuggestions.map((s, i) => (
              <div key={i} className="flex gap-3 items-start p-2.5 rounded-xl bg-blue-50 border border-blue-100">
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold flex-shrink-0 mt-0.5 ${
                  s.priority === "high" ? "bg-red-100 text-red-600" :
                  s.priority === "medium" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-500"
                }`}>{s.priority === "high" ? "高" : s.priority === "medium" ? "中" : "低"}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono text-blue-600 flex-shrink-0">{fmtTime(s.start)}</span>
                    <span className="text-xs font-semibold text-gray-800 truncate">{s.keyword}</span>
                    <span className="text-[10px] text-gray-400 flex-shrink-0">{s.b_roll_type}</span>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed">{s.description}</p>
                </div>
              </div>
            ))}
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
          <ProcessingView progress={job.progress || ""} progressPercent={job.progress_percent} />
        )}
        {job?.status === "completed" && <ResultsView job={job} />}
      </main>
      <Footer />
    </div>
  );
}
