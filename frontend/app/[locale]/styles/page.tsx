"use client";
import { useTranslations, useLocale } from "next-intl";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sparkles, Plus, Check, Pencil, Trash2, ChevronRight,
  Loader2, X, Wand2, Film, ChevronDown, BrainCircuit, Type, Dna, Store,
  Globe, EyeOff,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  listStyleProfiles, createStyleProfile, updateStyleProfile,
  deleteStyleProfile, activateStyleProfile,
  listReferenceVideos, addReferenceVideo, deleteReferenceVideo,
  aiRefineProfile, getProfileStats,
  publishStyleProfile, unpublishStyleProfile,
  ApiError,
  DEFAULT_CAPTION_STYLE,
  type StyleProfile, type ReferenceVideo, type ProfileStats, type CaptionStyle,
} from "@/lib/api";

type FormData = {
  name: string;
  description: string;
  noise_db: number;
  min_silence_seconds: number;
  default_prompt: string;
  caption_style: CaptionStyle;
};

const DEFAULT_FORM: FormData = {
  name: "",
  description: "",
  noise_db: -30,
  min_silence_seconds: 0.5,
  default_prompt: "",
  caption_style: { ...DEFAULT_CAPTION_STYLE },
};

function CaptionStyleSection({
  value,
  onChange,
}: {
  value: CaptionStyle;
  onChange: (cs: CaptionStyle) => void;
}) {
  const t = useTranslations("styles.form");
  const [open, setOpen] = useState(false);
  const set = <K extends keyof CaptionStyle>(k: K, v: CaptionStyle[K]) =>
    onChange({ ...value, [k]: v });

  const POSITION_OPTIONS: { value: CaptionStyle["position"]; label: string }[] = [
    { value: "bottom", label: t("captionBottom") },
    { value: "top", label: t("captionTop") },
    { value: "middle", label: t("captionMiddle") },
  ];

  const preview = (
    <span
      style={{
        fontWeight: value.bold ? "bold" : "normal",
        fontSize: Math.max(10, Math.round(value.font_size * 0.5)),
        color: value.primary_color,
        WebkitTextStroke: `1px ${value.outline_color}`,
        textShadow: `1px 1px 2px ${value.outline_color}`,
        letterSpacing: "0.01em",
      }}
    >
      {t("captionPreviewText")}
    </span>
  );

  return (
    <div className="border-t border-gray-100 pt-3 mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-purple-600 transition-colors"
      >
        <Type className="w-4 h-4" />
        {t("captionStyle")}
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {/* プレビュー */}
          <div className="bg-gray-800 rounded-xl h-14 flex items-end justify-center pb-2">
            {preview}
          </div>

          {/* フォントサイズ */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {t("captionFontSize")}: <span className="text-purple-600 font-bold">{value.font_size}px</span>
            </label>
            <input
              type="range" min="16" max="60" step="2" value={value.font_size}
              onChange={(e) => set("font_size", Number(e.target.value))}
              className="w-full accent-purple-600"
            />
          </div>

          {/* 位置 */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("captionPosition")}</label>
            <div className="flex gap-2">
              {POSITION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => set("position", opt.value)}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    value.position === opt.value
                      ? "border-purple-400 bg-purple-50 text-purple-700"
                      : "border-gray-200 text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 文字色 */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">{t("captionTextColor")}</label>
              <div className="flex items-center gap-2">
                <input
                  type="color" value={value.primary_color}
                  onChange={(e) => set("primary_color", e.target.value)}
                  className="w-8 h-8 rounded-lg border border-gray-200 cursor-pointer"
                />
                <span className="text-xs text-gray-400 font-mono">{value.primary_color.toUpperCase()}</span>
              </div>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">{t("captionOutlineColor")}</label>
              <div className="flex items-center gap-2">
                <input
                  type="color" value={value.outline_color}
                  onChange={(e) => set("outline_color", e.target.value)}
                  className="w-8 h-8 rounded-lg border border-gray-200 cursor-pointer"
                />
                <span className="text-xs text-gray-400 font-mono">{value.outline_color.toUpperCase()}</span>
              </div>
            </div>
          </div>

          {/* 太字 */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox" checked={value.bold}
              onChange={(e) => set("bold", e.target.checked)}
              className="w-4 h-4 rounded accent-purple-600"
            />
            <span className="text-xs font-medium text-gray-600">{t("captionBold")}</span>
          </label>

          {/* ズームエフェクト */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("zoomEffect")}</label>
            <div className="flex gap-2">
              {(["none", "subtle", "punch"] as const).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => set("zoom_effect", opt)}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    (value.zoom_effect ?? "none") === opt
                      ? "border-purple-400 bg-purple-50 text-purple-700"
                      : "border-gray-200 text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {opt === "none" ? t("zoomNone") : opt === "subtle" ? t("zoomSubtle") : t("zoomPunch")}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProfileForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: FormData;
  onSave: (data: FormData) => Promise<void>;
  onCancel: () => void;
}) {
  const t = useTranslations("styles.form");
  const [form, setForm] = useState<FormData>(initial ?? DEFAULT_FORM);
  const [saving, setSaving] = useState(false);

  const set = (k: keyof Omit<FormData, "caption_style">, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("name")}</label>
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder={t("namePlaceholder")}
          maxLength={80}
          required
          className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("description")}</label>
        <input
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
          placeholder={t("descriptionPlaceholder")}
          maxLength={200}
          className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">{t("noiseDb")}</label>
        <input
          type="range" min="-60" max="-10" value={form.noise_db}
          onChange={(e) => set("noise_db", Number(e.target.value))}
          className="w-full accent-purple-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>{t("sensitive")}</span>
          <span className="font-medium text-purple-700">{form.noise_db} dB</span>
          <span>{t("lenient")}</span>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t("minSilence")}: <span className="text-purple-600 font-bold">{form.min_silence_seconds}s</span>
        </label>
        <input
          type="range" min="0.1" max="3" step="0.1" value={form.min_silence_seconds}
          onChange={(e) => set("min_silence_seconds", Number(e.target.value))}
          className="w-full accent-purple-600"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("defaultPrompt")}</label>
        <textarea
          value={form.default_prompt}
          onChange={(e) => set("default_prompt", e.target.value)}
          placeholder={t("defaultPromptPlaceholder")}
          rows={3}
          maxLength={500}
          className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-400"
        />
      </div>

      <CaptionStyleSection
        value={form.caption_style}
        onChange={(cs) => setForm((f) => ({ ...f, caption_style: cs }))}
      />

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={saving || !form.name.trim()}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 disabled:opacity-50 text-sm"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          {initial ? t("save") : t("create")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2.5 border border-gray-200 text-gray-600 font-medium rounded-xl hover:bg-gray-50 text-sm"
        >
          {t("cancel")}
        </button>
      </div>
    </form>
  );
}

function ReferenceVideoSection({ profileId }: { profileId: string }) {
  const t = useTranslations("styles.referenceVideos");
  const [open, setOpen] = useState(false);
  const [videos, setVideos] = useState<ReferenceVideo[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    const { videos: v } = await listReferenceVideos(profileId);
    setVideos(v);
    setLoaded(true);
    setLoading(false);
  }

  async function toggle() {
    if (!open && !loaded) await load();
    setOpen((o) => !o);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || adding) return;
    setAdding(true);
    setError("");
    try {
      const v = await addReferenceVideo(profileId, url.trim());
      setVideos((prev) => [...prev, v]);
      setUrl("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("unsupportedError"));
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(videoId: string) {
    await deleteReferenceVideo(profileId, videoId);
    setVideos((prev) => prev.filter((v) => v.id !== videoId));
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-50">
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center gap-1.5 text-xs text-gray-400 hover:text-purple-600 transition-colors"
      >
        <Film className="w-3 h-3" />
        {t("title")}
        {loaded && videos.length > 0 && (
          <span className="bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full font-semibold">
            {videos.length}
          </span>
        )}
        <ChevronDown className={`w-3 h-3 ml-auto transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {loading ? (
            <div className="flex justify-center py-3">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            </div>
          ) : videos.length === 0 ? (
            <p className="text-xs text-gray-300 text-center py-2">{t("empty")}</p>
          ) : (
            videos.map((v) => (
              <div key={v.id} className="flex items-center gap-2 bg-gray-50 rounded-xl p-2">
                {v.oembed_thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={v.oembed_thumbnail_url}
                    alt=""
                    referrerPolicy="no-referrer"
                    className="w-14 h-9 object-cover rounded-lg flex-shrink-0 bg-gray-200"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-700 truncate">
                    {v.oembed_title || v.url}
                  </p>
                  {v.oembed_provider && (
                    <p className="text-xs text-gray-400">{v.oembed_provider}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(v.id)}
                  className="p-1 text-gray-300 hover:text-red-400 flex-shrink-0 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))
          )}

          <form onSubmit={handleAdd} className="flex gap-2 pt-1">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t("urlPlaceholder")}
              type="url"
              className="flex-1 text-xs px-3 py-1.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-400"
            />
            <button
              type="submit"
              disabled={adding || !url.trim()}
              className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white text-xs font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
              {t("add")}
            </button>
          </form>

          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>
      )}
    </div>
  );
}

function AiRefineSection({
  profile,
  onApply,
}: {
  profile: StyleProfile;
  onApply: (prompt: string) => Promise<void>;
}) {
  const t = useTranslations("styles");
  const [refining, setRefining] = useState(false);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [applying, setApplying] = useState(false);
  const [stats, setStats] = useState<ProfileStats | null>(null);

  useEffect(() => {
    getProfileStats(profile.id).then(setStats).catch(() => {});
  }, [profile.id]);

  async function handleRefine() {
    setRefining(true);
    setError("");
    setSuggestion(null);
    try {
      const { suggested_prompt } = await aiRefineProfile(profile.id);
      setSuggestion(suggested_prompt);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "エラーが発生しました");
    } finally {
      setRefining(false);
    }
  }

  async function handleApply() {
    if (!suggestion) return;
    setApplying(true);
    try {
      await onApply(suggestion);
      setSuggestion(null);
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-50">
      {suggestion ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-purple-700 flex items-center gap-1">
            <BrainCircuit className="w-3 h-3" /> {t("refineTitle")}
          </p>
          <p className="text-xs text-gray-700 bg-purple-50 rounded-xl p-3 leading-relaxed">
            {suggestion}
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleApply}
              disabled={applying}
              className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-purple-600 text-white text-xs font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50"
            >
              {applying ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
              {t("refineApply")}
            </button>
            <button
              onClick={() => setSuggestion(null)}
              className="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs rounded-xl hover:bg-gray-50"
            >
              {t("refineDismiss")}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-1.5">
          <button
            onClick={handleRefine}
            disabled={refining}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs text-purple-600 border border-purple-200 rounded-xl hover:bg-purple-50 disabled:opacity-50 transition-colors font-medium"
          >
            {refining
              ? <><Loader2 className="w-3 h-3 animate-spin" /> {t("refining")}</>
              : <><BrainCircuit className="w-3 h-3" /> {t("refine")}</>
            }
          </button>
          {error && <p className="text-xs text-red-500 text-center">{error}</p>}
          {!error && !refining && (
            <p className="text-xs text-gray-400 text-center">
              {stats && stats.total > 0
                ? t("refineHasFeedback", { count: stats.total })
                : t("refineNoFeedback")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function PublishSection({
  profile,
  onUpdate,
}: {
  profile: StyleProfile;
  onUpdate: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [desc, setDesc] = useState(profile.public_description ?? "");
  const [tags, setTags] = useState<string[]>(profile.tags ?? []);
  const [saving, setSaving] = useState(false);
  const ALL_TAGS = ["YouTube", "TikTok", "Podcast", "Interview", "Tutorial", "Vlog", "Talk", "SNS", "Business"];

  async function handlePublish() {
    setSaving(true);
    try {
      await publishStyleProfile(profile.id, desc, tags);
      onUpdate();
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleUnpublish() {
    setSaving(true);
    try {
      await unpublishStyleProfile(profile.id);
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  function toggleTag(tag: string) {
    setTags((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]);
  }

  if (profile.is_public) {
    return (
      <div className="mt-3 pt-3 border-t border-gray-50">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
            <Globe className="w-3 h-3" /> マーケットプレイスで公開中
            {profile.copy_count ? ` · ${profile.copy_count}コピー` : ""}
          </span>
          <button
            onClick={handleUnpublish}
            disabled={saving}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <EyeOff className="w-3 h-3" />}
            非公開にする
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-50">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs text-gray-400 border border-gray-200 rounded-xl hover:bg-gray-50 hover:text-purple-600 transition-colors font-medium"
        >
          <Globe className="w-3 h-3" /> マーケットプレイスに公開する
        </button>
      ) : (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-600 flex items-center gap-1">
            <Globe className="w-3 h-3 text-purple-500" /> 公開設定
          </p>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="このスタイルの説明（どんな動画に向いているか）"
            rows={2}
            maxLength={500}
            className="w-full text-xs px-3 py-2 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-400"
          />
          <div className="flex flex-wrap gap-1">
            {ALL_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={`px-2 py-0.5 rounded-full text-[11px] border transition-colors ${
                  tags.includes(tag)
                    ? "bg-purple-100 text-purple-700 border-purple-300"
                    : "bg-white text-gray-500 border-gray-200 hover:border-purple-200"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handlePublish}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-purple-600 text-white text-xs font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Globe className="w-3 h-3" />}
              公開する
            </button>
            <button
              onClick={() => setOpen(false)}
              className="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs rounded-xl hover:bg-gray-50"
            >
              キャンセル
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ProfileCard({
  profile,
  onActivate,
  onEdit,
  onDelete,
  onRefineApply,
  onUpdate,
}: {
  profile: StyleProfile;
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onRefineApply: (prompt: string) => Promise<void>;
  onUpdate: () => void;
}) {
  const t = useTranslations("styles");
  const locale = useLocale();
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!window.confirm(t("deleteConfirm"))) return;
    setDeleting(true);
    await onDelete();
  }

  return (
    <div className={`bg-white rounded-2xl border-2 p-5 transition-all ${
      profile.is_active ? "border-purple-400 shadow-lg shadow-purple-100" : "border-gray-100 hover:border-purple-200"
    }`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-bold text-gray-900 truncate">{profile.name}</h3>
            {profile.is_active && (
              <span className="flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
                <Sparkles className="w-3 h-3" /> {t("active")}
              </span>
            )}
          </div>
          {profile.description && (
            <p className="text-sm text-gray-400 mt-0.5 truncate">{profile.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={onEdit} className="p-1.5 text-gray-400 hover:text-purple-600 rounded-lg hover:bg-purple-50 transition-colors">
            <Pencil className="w-4 h-4" />
          </button>
          <button onClick={handleDelete} disabled={deleting} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50">
            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-gray-500 mb-4">
        <span className="bg-gray-50 px-2 py-1 rounded-lg">{profile.noise_db} dB</span>
        <span className="bg-gray-50 px-2 py-1 rounded-lg">{profile.min_silence_seconds}s</span>
        {profile.default_prompt && (
          <span className="bg-purple-50 text-purple-600 px-2 py-1 rounded-lg flex items-center gap-1">
            <Wand2 className="w-3 h-3" /> {t("aiPromptBadge")}
          </span>
        )}
        {profile.caption_style && (
          <span className="bg-blue-50 text-blue-600 px-2 py-1 rounded-lg flex items-center gap-1">
            <Type className="w-3 h-3" />
            {profile.caption_style.font_size}px · {profile.caption_style.position}
          </span>
        )}
        {profile.job_count > 0 && (
          <span className="bg-gray-50 px-2 py-1 rounded-lg">
            {t("jobCount", { count: profile.job_count })}
          </span>
        )}
      </div>

      <div className="flex gap-2">
        {!profile.is_active && (
          <button
            onClick={onActivate}
            className="flex-1 flex items-center justify-center gap-2 py-2 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 text-sm"
          >
            <Check className="w-4 h-4" /> {t("activate")}
          </button>
        )}
        <Link
          href={`/${locale}/upload`}
          className="flex items-center justify-center gap-1 px-4 py-2 border border-gray-200 text-gray-600 font-medium rounded-xl hover:bg-gray-50 text-sm"
        >
          {t("use")} <ChevronRight className="w-3 h-3" />
        </Link>
      </div>

      <ReferenceVideoSection profileId={profile.id} />
      <AiRefineSection profile={profile} onApply={onRefineApply} />
      <PublishSection profile={profile} onUpdate={onUpdate} />
    </div>
  );
}

export default function StylesPage() {
  const t = useTranslations("styles");
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingProfile, setEditingProfile] = useState<StyleProfile | null>(null);

  async function load() {
    setLoading(true);
    const { profiles } = await listStyleProfiles();
    setProfiles(profiles);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(data: FormData) {
    await createStyleProfile(data);
    setShowForm(false);
    await load();
  }

  async function handleUpdate(data: FormData) {
    if (!editingProfile) return;
    await updateStyleProfile(editingProfile.id, data);
    setEditingProfile(null);
    await load();
  }

  async function handleRefineApply(profileId: string, prompt: string) {
    await updateStyleProfile(profileId, { default_prompt: prompt });
    await load();
  }

  async function handleActivate(id: string) {
    await activateStyleProfile(id);
    await load();
  }

  async function handleDelete(id: string) {
    await deleteStyleProfile(id);
    await load();
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-3xl mx-auto">
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-black text-gray-900">{t("title")}</h1>
            <p className="text-gray-500 mt-1 text-sm">{t("subtitle")}</p>
          </div>
          {!showForm && !editingProfile && (
            <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
              <Link
                href={`/${locale}/styles/marketplace`}
                className="flex items-center gap-1.5 px-3 py-2 border border-pink-200 text-pink-600 font-medium rounded-xl hover:bg-pink-50 text-sm transition-colors"
              >
                <Store className="w-4 h-4" /> マーケット
              </Link>
              <Link
                href={`/${locale}/styles/analyze`}
                className="flex items-center gap-1.5 px-3 py-2 border border-purple-200 text-purple-600 font-medium rounded-xl hover:bg-purple-50 text-sm transition-colors"
              >
                <Dna className="w-4 h-4" /> {t("analyzeBtn")}
              </Link>
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 text-sm"
              >
                <Plus className="w-4 h-4" /> {t("new")}
              </button>
            </div>
          )}
        </div>

        {showForm && (
          <div className="bg-white rounded-2xl border border-purple-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900">{t("new")}</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <ProfileForm onSave={handleCreate} onCancel={() => setShowForm(false)} />
          </div>
        )}

        {editingProfile && (
          <div className="bg-white rounded-2xl border border-purple-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900">{t("edit")}: {editingProfile.name}</h2>
              <button onClick={() => setEditingProfile(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <ProfileForm
              initial={{
                name: editingProfile.name,
                description: editingProfile.description,
                noise_db: editingProfile.noise_db,
                min_silence_seconds: editingProfile.min_silence_seconds,
                default_prompt: editingProfile.default_prompt,
                caption_style: editingProfile.caption_style ?? { ...DEFAULT_CAPTION_STYLE },
              }}
              onSave={handleUpdate}
              onCancel={() => setEditingProfile(null)}
            />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        ) : profiles.length === 0 && !showForm ? (
          <div className="text-center py-16 text-gray-400">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">{t("empty")}</p>
            <p className="text-sm">{t("emptySub")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {profiles.map((p) => (
              <ProfileCard
                key={p.id}
                profile={p}
                onActivate={() => handleActivate(p.id)}
                onEdit={() => { setEditingProfile(p); setShowForm(false); }}
                onDelete={() => handleDelete(p.id)}
                onRefineApply={(prompt) => handleRefineApply(p.id, prompt)}
                onUpdate={load}
              />
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
