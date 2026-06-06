"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft, Store, Copy, CheckCircle, Loader2,
  Users, Tag, Zap, ChevronDown,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  listMarketplaceProfiles,
  copyMarketplaceProfile,
  type PublicStyleProfile,
} from "@/lib/api";

const ALL_TAGS = ["YouTube", "TikTok", "Podcast", "Interview", "Tutorial", "Vlog", "Talk", "Documentary", "SNS", "Business"];

function ProfileCard({
  profile,
  onCopy,
  copying,
  copied,
}: {
  profile: PublicStyleProfile;
  onCopy: (id: string) => void;
  copying: boolean;
  copied: boolean;
}) {
  const locale = useLocale();
  const cs = profile.caption_style;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-bold text-gray-900 text-base">{profile.name}</h3>
          {profile.public_description && (
            <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{profile.public_description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-400 shrink-0">
          <Copy className="w-3.5 h-3.5" />
          {profile.copy_count ?? 0}
        </div>
      </div>

      {/* stats */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-gray-50 rounded-xl px-2 py-1.5 text-center">
          <p className="text-gray-400">ノイズ閾値</p>
          <p className="font-semibold text-gray-700">{profile.noise_db} dB</p>
        </div>
        <div className="bg-gray-50 rounded-xl px-2 py-1.5 text-center">
          <p className="text-gray-400">無音最小</p>
          <p className="font-semibold text-gray-700">{profile.min_silence_seconds}s</p>
        </div>
        <div className="bg-gray-50 rounded-xl px-2 py-1.5 text-center">
          <p className="text-gray-400">ズーム</p>
          <p className="font-semibold text-gray-700">{cs?.zoom_effect ?? "none"}</p>
        </div>
      </div>

      {/* caption preview */}
      {cs && (
        <div className="bg-gray-900 rounded-xl px-3 py-2 text-center text-xs">
          <span
            style={{
              color: cs.primary_color,
              WebkitTextStroke: `0.5px ${cs.outline_color}`,
              fontWeight: cs.bold ? "bold" : "normal",
              fontSize: `${Math.max(10, Math.min(16, cs.font_size / 2))}px`,
            }}
          >
            テロップのプレビュー
          </span>
        </div>
      )}

      {/* tags */}
      {profile.tags && profile.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {profile.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-purple-50 text-purple-600 text-[11px] rounded-full border border-purple-100"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* prompt preview */}
      {profile.default_prompt && (
        <p className="text-xs text-gray-400 italic line-clamp-2 border-t border-gray-50 pt-2">
          &ldquo;{profile.default_prompt}&rdquo;
        </p>
      )}

      <button
        onClick={() => onCopy(profile.id)}
        disabled={copying || copied}
        className={`mt-auto flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all ${
          copied
            ? "bg-green-100 text-green-700 border border-green-200"
            : "bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:opacity-90 disabled:opacity-50"
        }`}
      >
        {copying ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> コピー中...</>
        ) : copied ? (
          <><CheckCircle className="w-4 h-4" /> コピー済み</>
        ) : (
          <><Copy className="w-4 h-4" /> 自分のプロファイルにコピー</>
        )}
      </button>
    </div>
  );
}

export default function MarketplacePage() {
  const t = useTranslations("marketplace");
  const locale = useLocale();
  const [profiles, setProfiles] = useState<PublicStyleProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedIds, setCopiedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async (tag?: string) => {
    setLoading(true);
    try {
      const { profiles: data } = await listMarketplaceProfiles(tag || undefined);
      setProfiles(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(activeTag ?? undefined);
  }, [activeTag, load]);

  async function handleCopy(profileId: string) {
    if (copyingId || copiedIds.has(profileId)) return;
    setCopyingId(profileId);
    try {
      await copyMarketplaceProfile(profileId);
      setCopiedIds((prev) => new Set([...prev, profileId]));
    } catch (e) {
      console.error(e);
    } finally {
      setCopyingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-5xl mx-auto">
        <div className="mb-8">
          <Link
            href={`/${locale}/styles`}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-purple-600 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" /> スタイル一覧へ
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
              <Store className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-gray-900">{t("title")}</h1>
              <p className="text-sm text-gray-500">{t("subtitle")}</p>
            </div>
          </div>
        </div>

        {/* Tag filter */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setActiveTag(null)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors border ${
              activeTag === null
                ? "bg-purple-600 text-white border-purple-600"
                : "bg-white text-gray-600 border-gray-200 hover:border-purple-300"
            }`}
          >
            すべて
          </button>
          {ALL_TAGS.map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveTag(activeTag === tag ? null : tag)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors border ${
                activeTag === tag
                  ? "bg-purple-600 text-white border-purple-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-purple-300"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center py-24 text-gray-400">
            <Store className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">{t("empty")}</p>
            <p className="text-sm mt-1">{t("emptyHint")}</p>
            <Link
              href={`/${locale}/styles`}
              className="mt-4 inline-block text-sm text-purple-600 underline"
            >
              自分のプロファイルを公開する
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {profiles.map((p) => (
              <ProfileCard
                key={p.id}
                profile={p}
                onCopy={handleCopy}
                copying={copyingId === p.id}
                copied={copiedIds.has(p.id)}
              />
            ))}
          </div>
        )}

        {/* stats bar */}
        {!loading && profiles.length > 0 && (
          <p className="text-center text-xs text-gray-400 mt-8">
            {profiles.length} 件のスタイルプロファイル
          </p>
        )}
      </main>

      <Footer />
    </div>
  );
}
