"use client";
import { useTranslations, useLocale } from "next-intl";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, CreditCard, LogOut, ChevronRight, Film, Loader2, Plug, Copy, Check, Users, UserPlus, X, Mail, Shield, Key, Webhook, Plus, Trash2, ExternalLink } from "lucide-react";
import Header from "@/components/Header";
import { createClient } from "@/lib/supabase";
import {
  getUserUsage, getBillingPortal,
  getTeam, inviteTeamMember, removeTeamMember,
  listApiKeys, createApiKey, revokeApiKey,
  listWebhooks, createWebhook, deleteWebhook,
  type UsageResponse, type TeamMember, type ApiKey, type Webhook as WebhookType,
} from "@/lib/api";

const PLANS = [
  { key: "free", price: "¥0", limit_ja: "月3本 / 最大3分", limit_en: "3/mo · up to 3 min" },
  { key: "pro", price: "¥980/月", limit_ja: "月30本 / 最大15分", limit_en: "30/mo · up to 15 min" },
  { key: "creator", price: "¥2,980/月", limit_ja: "月100本 / 最大60分", limit_en: "100/mo · up to 60 min" },
  { key: "studio", price: "¥9,800/月", limit_ja: "無制限", limit_en: "Unlimited" },
];

export default function AccountPage() {
  const t = useTranslations("account");
  const locale = useLocale();
  const router = useRouter();
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [email, setEmail] = useState<string>("");
  const [token, setToken] = useState<string>("");
  const [tokenCopied, setTokenCopied] = useState(false);
  const [loadingPortal, setLoadingPortal] = useState(false);
  // API key state
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [newRawKey, setNewRawKey] = useState("");
  const [newKeyCopied, setNewKeyCopied] = useState(false);
  // Webhook state
  const [webhooks, setWebhooks] = useState<WebhookType[]>([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [creatingWebhook, setCreatingWebhook] = useState(false);
  const [webhookSecret, setWebhookSecret] = useState("");
  const [webhookSecretCopied, setWebhookSecretCopied] = useState(false);
  // Team state
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"editor" | "admin">("editor");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [inviteSuccess, setInviteSuccess] = useState("");

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (data.user?.email) setEmail(data.user.email);
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data.session?.access_token) setToken(data.session.access_token);
    });
    getUserUsage().then((u) => {
      setUsage(u);
      if (u.plan === "studio") {
        getTeam().then((d) => setTeamMembers(d.my_team.members)).catch(() => {});
      }
    }).catch(() => {});
    listApiKeys().then(setApiKeys).catch(() => {});
    listWebhooks().then(setWebhooks).catch(() => {});
  }, []);

  async function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setInviteError("");
    setInviteSuccess("");
    try {
      await inviteTeamMember(inviteEmail.trim(), inviteRole);
      setInviteSuccess(inviteEmail.trim() + " に招待を送りました");
      setInviteEmail("");
      const d = await getTeam();
      setTeamMembers(d.my_team.members);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setInviteError(err?.message ?? "招待に失敗しました");
    } finally {
      setInviting(false);
    }
  }

  async function handleRemoveMember(id: string) {
    try {
      await removeTeamMember(id);
      setTeamMembers((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // silent
    }
  }

  async function handleCreateApiKey() {
    if (!newKeyName.trim()) return;
    setCreatingKey(true);
    try {
      const key = await createApiKey(newKeyName.trim());
      setApiKeys((prev) => [key, ...prev]);
      setNewRawKey(key.raw_key ?? "");
      setNewKeyName("");
    } catch { /* silent */ } finally {
      setCreatingKey(false);
    }
  }

  async function handleRevokeApiKey(id: string) {
    await revokeApiKey(id).catch(() => {});
    setApiKeys((prev) => prev.filter((k) => k.id !== id));
  }

  async function handleCreateWebhook() {
    if (!newWebhookUrl.trim()) return;
    setCreatingWebhook(true);
    try {
      const wh = await createWebhook(newWebhookUrl.trim());
      setWebhooks((prev) => [wh, ...prev]);
      setWebhookSecret(wh.secret ?? "");
      setNewWebhookUrl("");
    } catch { /* silent */ } finally {
      setCreatingWebhook(false);
    }
  }

  async function handleDeleteWebhook(id: string) {
    await deleteWebhook(id).catch(() => {});
    setWebhooks((prev) => prev.filter((w) => w.id !== id));
  }

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
        <h1 className="text-3xl font-black text-gray-900 mb-8">{t("title")}</h1>

        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <h2 className="font-bold text-gray-900">{t("profile")}</h2>
            </div>
            <div className="text-sm text-gray-500">
              <p className="mb-1">{t("emailLabel")}</p>
              <p className="text-gray-900 font-medium">{email || "..."}</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-white" />
                </div>
                <h2 className="font-bold text-gray-900">{t("planSection")}</h2>
              </div>
              {currentPlan !== "free" && (
                <button
                  onClick={handleBillingPortal}
                  disabled={loadingPortal}
                  className="flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 font-medium disabled:opacity-50"
                >
                  {loadingPortal ? <Loader2 className="w-3 h-3 animate-spin" /> : <ChevronRight className="w-3 h-3" />}
                  {t("billing")}
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
                      <p className="font-semibold text-gray-900 text-sm capitalize">{plan.key}</p>
                      <p className="text-xs text-gray-400">
                        {locale === "ja" ? plan.limit_ja : plan.limit_en}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-700">{plan.price}</span>
                    {plan.key === currentPlan ? (
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                        {t("currentBadge")}
                      </span>
                    ) : plan.key !== "free" && (
                      <button
                        onClick={handleBillingPortal}
                        className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700 font-medium"
                      >
                        {t("changePlan")} <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {usage && usage.limit !== null && (
              <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-500">
                {t("usageThisMonth")}:{" "}
                <span className="font-bold text-gray-900">
                  {usage.used} / {usage.limit}
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

          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Plug className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">{t("pluginTitle")}</h2>
                <p className="text-xs text-gray-400">{t("pluginSubtitle")}</p>
              </div>
            </div>
            <p className="text-sm text-gray-500 mb-3">{t("pluginDescription")}</p>
            <div className="flex gap-2">
              <input
                readOnly
                value={token ? `${token.slice(0, 40)}...` : "..."}
                className="flex-1 px-3 py-2 text-xs font-mono bg-gray-50 border border-gray-200 rounded-lg text-gray-600 select-all"
              />
              <button
                onClick={copyToken}
                disabled={!token}
                className="flex items-center gap-1.5 px-3 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {tokenCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {tokenCopied ? t("copied") : t("copy")}
              </button>
            </div>
          </div>

          {/* API Keys */}
          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-slate-600 to-gray-700 rounded-xl flex items-center justify-center">
                <Key className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">外部APIキー</h2>
                <p className="text-xs text-gray-400">スクリプト・外部ツールからAPI呼び出しに使用</p>
              </div>
            </div>

            {/* 新規作成フォーム */}
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                placeholder="キー名（例: my-script）"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateApiKey()}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-purple-400"
              />
              <button
                onClick={handleCreateApiKey}
                disabled={creatingKey || !newKeyName.trim()}
                className="flex items-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {creatingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                生成
              </button>
            </div>

            {/* 生成直後のキー表示 */}
            {newRawKey && (
              <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
                <p className="text-xs text-yellow-700 font-medium mb-1.5">このキーは一度だけ表示されます。必ずコピーしてください。</p>
                <div className="flex gap-2">
                  <input
                    readOnly
                    value={newRawKey}
                    className="flex-1 px-2 py-1.5 text-xs font-mono bg-white border border-yellow-200 rounded-lg select-all text-gray-700"
                  />
                  <button
                    onClick={async () => {
                      await navigator.clipboard.writeText(newRawKey);
                      setNewKeyCopied(true);
                      setTimeout(() => { setNewKeyCopied(false); setNewRawKey(""); }, 3000);
                    }}
                    className="px-2.5 py-1.5 bg-yellow-100 hover:bg-yellow-200 text-yellow-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    {newKeyCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            )}

            {/* キー一覧 */}
            {apiKeys.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-2">APIキーがありません</p>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((k) => (
                  <div key={k.id} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{k.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{k.key_prefix}...</p>
                    </div>
                    <button
                      onClick={() => handleRevokeApiKey(k.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="キーを無効化"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Webhooks */}
          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-pink-500 rounded-xl flex items-center justify-center">
                <Webhook className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">Webhook</h2>
                <p className="text-xs text-gray-400">ジョブ完了・失敗時に指定URLへHTTP POSTを送信</p>
              </div>
            </div>

            {/* 新規登録フォーム */}
            <div className="flex gap-2 mb-3">
              <input
                type="url"
                placeholder="https://your-server.com/webhook"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateWebhook()}
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-purple-400"
              />
              <button
                onClick={handleCreateWebhook}
                disabled={creatingWebhook || !newWebhookUrl.trim()}
                className="flex items-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {creatingWebhook ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                追加
              </button>
            </div>

            {/* シークレット表示 */}
            {webhookSecret && (
              <div className="mb-3 p-3 bg-orange-50 border border-orange-200 rounded-xl">
                <p className="text-xs text-orange-700 font-medium mb-1.5">署名シークレット（一度だけ表示）。X-EditClone-Signature ヘッダーで検証できます。</p>
                <div className="flex gap-2">
                  <input
                    readOnly
                    value={webhookSecret}
                    className="flex-1 px-2 py-1.5 text-xs font-mono bg-white border border-orange-200 rounded-lg select-all text-gray-700"
                  />
                  <button
                    onClick={async () => {
                      await navigator.clipboard.writeText(webhookSecret);
                      setWebhookSecretCopied(true);
                      setTimeout(() => { setWebhookSecretCopied(false); setWebhookSecret(""); }, 3000);
                    }}
                    className="px-2.5 py-1.5 bg-orange-100 hover:bg-orange-200 text-orange-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    {webhookSecretCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            )}

            {/* Webhook一覧 */}
            {webhooks.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-2">Webhookが登録されていません</p>
            ) : (
              <div className="space-y-2">
                {webhooks.map((w) => (
                  <div key={w.id} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-gray-700 truncate">{w.url}</p>
                      <p className="text-[10px] text-gray-400">{w.events.join(", ")}</p>
                    </div>
                    <a href={w.url} target="_blank" rel="noopener noreferrer" className="p-1.5 text-gray-400 hover:text-blue-500 transition-colors">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                    <button
                      onClick={() => handleDeleteWebhook(w.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="削除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Team Management — Studio only */}
          {currentPlan === "studio" && (
            <div className="bg-white rounded-2xl p-6 border border-gray-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-teal-600 rounded-xl flex items-center justify-center">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-gray-900">チーム管理</h2>
                  <p className="text-xs text-gray-400">Studio プラン限定・スタイルプロファイルを共有</p>
                </div>
              </div>

              {/* Invite form */}
              <div className="flex gap-2 mb-3">
                <div className="relative flex-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="email"
                    placeholder="メールアドレス"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                    className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-purple-400"
                  />
                </div>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as "editor" | "admin")}
                  className="px-2 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-purple-400 bg-white"
                >
                  <option value="editor">編集者</option>
                  <option value="admin">管理者</option>
                </select>
                <button
                  onClick={handleInvite}
                  disabled={inviting || !inviteEmail.trim()}
                  className="flex items-center gap-1.5 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {inviting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserPlus className="w-3.5 h-3.5" />}
                  招待
                </button>
              </div>

              {inviteError && (
                <p className="text-xs text-red-500 mb-2">{inviteError}</p>
              )}
              {inviteSuccess && (
                <p className="text-xs text-green-600 mb-2">{inviteSuccess}</p>
              )}

              {/* Members list */}
              {teamMembers.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-3">メンバーがいません</p>
              ) : (
                <div className="space-y-2">
                  {teamMembers.map((m) => (
                    <div key={m.id} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                          m.status === "accepted" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                        }`}>
                          {m.invited_email[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-800">{m.invited_email}</p>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400 flex items-center gap-0.5">
                              <Shield className="w-3 h-3" />
                              {m.role === "admin" ? "管理者" : "編集者"}
                            </span>
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                              m.status === "accepted"
                                ? "bg-green-100 text-green-700"
                                : "bg-yellow-100 text-yellow-700"
                            }`}>
                              {m.status === "accepted" ? "参加中" : "招待中"}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemoveMember(m.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="メンバーを削除"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-4 border border-red-200 text-red-500 hover:bg-red-50 rounded-2xl transition-colors font-medium"
          >
            <LogOut className="w-5 h-5" />
            {t("logout")}
          </button>
        </div>
      </main>
    </div>
  );
}
