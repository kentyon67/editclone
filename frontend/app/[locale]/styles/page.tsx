"use client";
import { useTranslations, useLocale } from "next-intl";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sparkles, Plus, Check, Pencil, Trash2, ChevronRight,
  Loader2, X, Wand2,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  listStyleProfiles, createStyleProfile, updateStyleProfile,
  deleteStyleProfile, activateStyleProfile, type StyleProfile,
} from "@/lib/api";

type FormData = {
  name: string;
  description: string;
  noise_db: number;
  min_silence_seconds: number;
  default_prompt: string;
};

const DEFAULT_FORM: FormData = {
  name: "",
  description: "",
  noise_db: -30,
  min_silence_seconds: 0.5,
  default_prompt: "",
};

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

  const set = (k: keyof FormData, v: string | number) =>
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
          <span>敏感</span>
          <span className="font-medium text-purple-700">{form.noise_db} dB</span>
          <span>鈍感</span>
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

function ProfileCard({
  profile,
  onActivate,
  onEdit,
  onDelete,
}: {
  profile: StyleProfile;
  onActivate: () => void;
  onEdit: () => void;
  onDelete: () => void;
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
            <Wand2 className="w-3 h-3" /> AI指示あり
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
          使う <ChevronRight className="w-3 h-3" />
        </Link>
      </div>
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
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-xl hover:opacity-90 text-sm flex-shrink-0"
            >
              <Plus className="w-4 h-4" /> {t("new")}
            </button>
          )}
        </div>

        {/* 新規作成フォーム */}
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

        {/* 編集フォーム */}
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
              }}
              onSave={handleUpdate}
              onCancel={() => setEditingProfile(null)}
            />
          </div>
        )}

        {/* プロファイル一覧 */}
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
              />
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
