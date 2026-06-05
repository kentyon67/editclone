"use client";
import { useLocale } from "next-intl";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, CreditCard, LogOut, ChevronRight, Film, Loader2, Plug, Copy, Check } from "lucide-react";
import Header from "@/components/Header";
import { createClient } from "@/lib/supabase";
import { getUserUsage, getBillingPortal, type UsageResponse } from "@/lib/api";

const PLANS = [
  { key: "free", name: "Free", price: "¥0", limit: "月3本 / 最大3分" },
  { key: "pro", name: "Pro", price: "¥980/月", limit: "月30本 / 最大15分" },
  { key: "creator", name: "Creator", price: "¥2,980/月", limit: "月100本 / 最大60分" },
  { key: "studio", name: "Studio", price: "¥9,800/月", limit: "無制限" },
];

export default function AccountPage() {
  const locale = useLocale();
  const router = useRouter();
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [email, setEmail] = useState<string>("");
  const [token, setToken] = useState<string>("");
  const [tokenCopied, setTokenCopied] = useState(false);
  const [loadingPortal, setLoadingPortal] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (data.user?.email) setEmail(data.user.email);
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.access_token) setToken(data.session.access_token);
    });
    getUserUsage().then(setUsage).catch(() => {});
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push(`/${locale}`);
  }

  async function copyToken() {
    if (!token) return;
    await navigator.clipboard.writeText(token);
    setTokenCopied(true);
    setTimeout(() => setTokenCopied(false), 2500);
  }

  async function handleBillingPortal() {
    setLoadingPortal(true);
    try {
      const returnUrl = `${window.location.origin}/${locale}/account`;
      const { portal_url } = await getBillingPortal(returnUrl);
      window.location.href = portal_url;
    } catch {
      setLoadingPortal(false);
    }
  }

  const currentPlan = usage?.plan ?? "free";

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isLoggedIn />

      <main className="pt-24 pb-16 px-4 max-w-2xl mx-auto">
        <h1 className="text-3xl font-black text-gray-900 mb-8">アカウント</h1>

        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <h2 className="font-bold text-gray-900">プロフィール</h2>
            </div>
            <div className="text-sm text-gray-500">
              <p className="mb-1">メールアドレス</p>
              <p className="text-gray-900 font-medium">{email || "..."}</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-white" />
                </div>
                <h2 className="font-bold text-gray-900">プラン</h2>
              </div>
              {currentPlan !== "free" && (
                <button
                  onClick={handleBillingPortal}
                  disabled={loadingPortal}
                  className="flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 font-medium disabled:opacity-50"
                >
                  {loadingPortal ? <Loader2 className="w-3 h-3 animate-spin" /> : <ChevronRight className="w-3 h-3" />}
                  請求管理
                </button>
              )}
            </div>

            <div className="space-y-3">
              {PLANS.map((plan) => (
                <div
                  key={plan.key}
                  className={`flex items-center justify-between p-3 rounded-xl border ${
                    plan.key === currentPlan
                      ? "border-purple-300 bg-purple-50"
                      : "border-gray-100"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Film className={`w-4 h-4 ${plan.key === currentPlan ? "text-purple-500" : "text-gray-300"}`} />
                    <div>
                      <p className="font-semibold text-gray-900 text-sm">{plan.name}</p>
                      <p className="text-xs text-gray-400">{plan.limit}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-700">{plan.price}</span>
                    {plan.key === currentPlan ? (
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">現在</span>
                    ) : plan.key !== "free" && (
                      <button
                        onClick={handleBillingPortal}
                        className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700 font-medium"
                      >
                        変更 <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {usage && usage.limit !== null && (
              <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-500">
                今月の利用:{" "}
                <span className="font-bold text-gray-900">
                  {usage.used} / {usage.limit} 本
                </span>
                <div className="mt-2 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all"
                    style={{ width: `${Math.min(100, (usage.used / usage.limit) * 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Plugin token section */}
          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Plug className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">NLE プラグイン連携</h2>
                <p className="text-xs text-gray-400">Premiere / FCP / DaVinci</p>
              </div>
            </div>
            <p className="text-sm text-gray-500 mb-3">
              プラグインのログイン画面でこのトークンを貼り付けてください。トークンは1時間で期限切れになります。
            </p>
            <div className="flex gap-2">
              <input
                readOnly
                value={token ? `${token.slice(0, 40)}...` : "読み込み中..."}
                className="flex-1 px-3 py-2 text-xs font-mono bg-gray-50 border border-gray-200 rounded-lg text-gray-600 select-all"
              />
              <button
                onClick={copyToken}
                disabled={!token}
                className="flex items-center gap-1.5 px-3 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {tokenCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {tokenCopied ? "コピー済み" : "コピー"}
              </button>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-4 border border-red-200 text-red-500 hover:bg-red-50 rounded-2xl transition-colors font-medium"
          >
            <LogOut className="w-5 h-5" />
            ログアウト
          </button>
        </div>
      </main>
    </div>
  );
}
