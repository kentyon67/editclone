"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useCallback, useRef } from "react";
import Link from "next/link";
import { Image as ImageIcon, ArrowLeft, Loader2, Download, X, GripVertical } from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { createSlideshow, ApiError } from "@/lib/api";

export default function SlideshowPage() {
  const t = useTranslations("slideshow");
  const locale = useLocale();
  const inputRef = useRef<HTMLInputElement>(null);
  const [images, setImages] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [durationPerSlide, setDurationPerSlide] = useState(3);
  const [transition, setTransition] = useState<"fade" | "none">("fade");
  const [generating, setGenerating] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  const addFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    const allowed = [".jpg", ".jpeg", ".png", ".webp"];
    const valid = Array.from(files).filter((f) =>
      allowed.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setImages((prev) => {
      const combined = [...prev, ...valid];
      return combined.slice(0, 50);
    });
    setDownloadUrl(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  function removeImage(index: number) {
    setImages((prev) => prev.filter((_, i) => i !== index));
    setDownloadUrl(null);
  }

  async function handleGenerate() {
    if (images.length === 0) return;
    setGenerating(true);
    setError("");
    setDownloadUrl(null);
    try {
      const blob = await createSlideshow(images, {
        duration_per_slide: durationPerSlide,
        transition,
      });
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "生成に失敗しました");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/${locale}/upload`}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-purple-600 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" /> 動画アップロードへ戻る
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-400 to-pink-600 flex items-center justify-center">
              <ImageIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-gray-900">{t("title")}</h1>
              <p className="text-sm text-gray-500">{t("subtitle")}</p>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed transition-all py-12 flex flex-col items-center gap-3 ${
              dragging
                ? "border-orange-400 bg-orange-50"
                : "border-gray-200 bg-white hover:border-orange-300 hover:bg-orange-50/50"
            }`}
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-400 to-pink-600 flex items-center justify-center">
              <ImageIcon className="w-6 h-6 text-white" />
            </div>
            <p className="font-semibold text-gray-700">{t("dropzone")}</p>
            <p className="text-xs text-gray-400">{t("formats")}</p>
            <input
              ref={inputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              multiple
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {/* Image grid */}
          {images.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold text-gray-700">
                  {t("imageCount", { count: images.length })}
                </p>
                <button
                  onClick={() => inputRef.current?.click()}
                  className="text-xs text-purple-600 hover:text-purple-800 font-medium"
                >
                  + 追加
                </button>
              </div>
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                {images.map((img, i) => (
                  <div key={i} className="relative group aspect-square">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={URL.createObjectURL(img)}
                      alt={img.name}
                      className="w-full h-full object-cover rounded-lg"
                    />
                    <button
                      onClick={() => removeImage(i)}
                      className="absolute top-0.5 right-0.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    <div className="absolute bottom-0.5 left-0.5 w-5 h-5 bg-black/50 text-white rounded text-[10px] flex items-center justify-center">
                      {i + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings */}
          <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                {t("durationLabel")}: <span className="text-orange-500 font-bold">{t("durationValue", { duration: durationPerSlide })}</span>
              </label>
              <input
                type="range" min="1" max="10" step="0.5" value={durationPerSlide}
                onChange={(e) => setDurationPerSlide(Number(e.target.value))}
                className="w-full accent-orange-500"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>1秒</span>
                <span>10秒</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">{t("transitionLabel")}</label>
              <div className="flex gap-3">
                {(["fade", "none"] as const).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => setTransition(opt)}
                    className={`flex-1 py-2 text-sm font-medium rounded-xl border transition-colors ${
                      transition === opt
                        ? "border-orange-400 bg-orange-50 text-orange-700"
                        : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {opt === "fade" ? t("transitionFade") : t("transitionNone")}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-xl">
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={images.length === 0 || generating}
            className="w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-orange-400 to-pink-600 text-white font-bold rounded-xl hover:opacity-90 disabled:opacity-50 text-base"
          >
            {generating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {t("generating")}
              </>
            ) : (
              <>
                <ImageIcon className="w-5 h-5" />
                {t("generate")}
              </>
            )}
          </button>

          {generating && (
            <p className="text-center text-sm text-gray-500 animate-pulse">{t("generating2")}</p>
          )}

          {downloadUrl && (
            <a
              href={downloadUrl}
              download="slideshow.mp4"
              className="w-full flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold rounded-xl hover:opacity-90 text-base"
            >
              <Download className="w-5 h-5" />
              {t("downloadMp4")}
            </a>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
