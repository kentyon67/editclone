"use client";
import { useTranslations, useLocale } from "next-intl";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft, Store, Copy, CheckCircle, Loader2,
  Star, ChevronDown, ChevronUp, Search, X,
} from "lucide-react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import {
  listMarketplaceProfiles,
  copyMarketplaceProfile,
  addMarketplaceReview,
  getMarketplaceReviews,
  type PublicStyleProfile,
  type ReviewStats,
} from "@/lib/api";

const ALL_TAGS = ["YouTube", "TikTok", "Podcast", "Interview", "Tutorial", "Vlog", "Talk", "Documentary", "SNS", "Business"];

function StarPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          className="text-xl leading-none transition-transform hover:scale-110"
          aria-label={`${n}星`}
        >
          <Star
            className={`w-5 h-5 ${n <= (hover || value) ? "fill-yellow-400 text-yellow-400" : "text-gray-200"}`}
          />
        </button>
      ))}
    </div>
  );
}

function StarDisplay({ average, count }: { average: number; count: number }) {
  const filled = Math.round(average);
  return (
    <div className="flex items-center gap-1">
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <Star key={n} className={`w-3.5 h-3.5 ${n <= filled ? "fill-yellow-400 text-yellow-400" : "text-gray-200"}`} />
        ))}
      </div>
      <span className="text-xs text-gray-500">
        {count > 0 ? `${average.toFixed(1)} (${count})` : "未評価"}
      </span>
    </div>
  );
}

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
  const cs = profile.caption_style;
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null);
  const [userRating, setUserRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function loadStats() {
    const data = await getMarketplaceReviews(profile.id);
    setReviewStats(data.stats);
  }

  async function handleSubmitReview() {
    if (!userRating) return;
    setSubmitting(true);
    try {
      await addMarketplaceReview(profile.id, userRating, reviewText);
      setSubmitted(true);
      await loadStats();
    } catch {
      // silent
    } finally {
      setSubmitting(false);
    }
  }

  function handleToggleReview() {
    const next = !reviewOpen;
    setReviewOpen(next);
    if (next && !reviewStats) loadStats();
  }

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

      {/* Review toggle */}
      <button
        type="button"
        onClick={handleToggleReview}
        className="flex items-center justify-between text-xs text-gray-500 hover:text-purple-600 transition-colors pt-1 border-t border-gray-50"
      >
        <span className="flex items-center gap-1">
          <Star className="w-3.5 h-3.5" />
          {reviewStats
            ? <StarDisplay average={reviewStats.average} count={reviewStats.count} />
            : "評価・レビュー"}
        </span>
        {reviewOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {reviewOpen && (
        <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-2">
          {submitted ? (
            <p className="text-xs text-green-600 text-center font-medium">レビューを投稿しました！</p>
          ) : (
            <>
              <p className="text-xs text-gray-500 font-medium">このスタイルを評価</p>
              <StarPicker value={userRating} onChange={setUserRating} />
              <textarea
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="コメント（任意）"
                rows={2}
                className="text-xs p-2 border border-gray-200 rounded-lg resize-none focus:outline-none focus:border-purple-400 bg-white"
                maxLength={200}
              />
              <button
                onClick={handleSubmitReview}
                disabled={!userRating || submitting}
                className="flex items-center justify-center gap-1.5 py-1.5 bg-purple-600 text-white text-xs font-semibold rounded-lg disabled:opacity-40 hover:bg-purple-700 transition-colors"
              >
                {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Star className="w-3 h-3" />}
                投稿
              </button>
            </>
          )}
          {reviewStats && reviewStats.count > 0 && (
            <div className="mt-1 flex flex-col gap-0.5">
              {[5, 4, 3, 2, 1].map((star) => {
                const cnt = reviewStats.distribution[String(star)] ?? 0;
                const pct = reviewStats.count > 0 ? (cnt / reviewStats.count) * 100 : 0;
                return (
                  <div key={star} className="flex items-center gap-1.5 text-[10px] text-gray-400">
                    <span className="w-2">{star}</span>
                    <Star className="w-2.5 h-2.5 fill-yellow-400 text-yellow-400" />
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-yellow-400 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-4 text-right">{cnt}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
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
  const [searchQuery, setSearchQuery] = useState("");
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedIds, setCopiedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async (tag?: string, q?: string) => {
    setLoading(true);
    try {
      const { profiles: data } = await listMarketplaceProfiles(tag || undefined, q || undefined);
      setProfiles(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      load(activeTag ?? undefined, searchQuery || undefined);
    }, searchQuery ? 400 : 0);
    return () => clearTimeout(timer);
  }, [activeTag, searchQuery, load]);

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

        {/* 検索ボックス */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="プロファイル名・説明・タグで検索..."
            className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
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
