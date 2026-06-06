"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import Link from "next/link";
import { Users, CheckCircle, XCircle, Loader2, Shield, ArrowRight, LogIn } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { getTeamInviteInfo, acceptTeamInvite } from "@/lib/api";

const ROLE_LABELS: Record<string, string> = {
  editor: "編集者",
  admin: "管理者",
};

export default function TeamInvitePage({
  params,
}: {
  params: { token: string; locale: string };
}) {
  const locale = useLocale();
  const router = useRouter();
  const { token } = params;

  const [inviteInfo, setInviteInfo] = useState<{
    invited_email: string;
    role: string;
    status: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentEmail, setCurrentEmail] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function init() {
      // 招待情報取得（認証不要）
      try {
        const info = await getTeamInviteInfo(token);
        setInviteInfo(info);
      } catch {
        setError("招待が見つかりませんでした。リンクが無効または期限切れの可能性があります。");
      }

      // 現在のログインユーザーを確認
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      if (data.user?.email) setCurrentEmail(data.user.email);

      setLoading(false);
    }
    init();
  }, [token]);

  async function handleAccept() {
    setAccepting(true);
    setError("");
    try {
      await acceptTeamInvite(token);
      setAccepted(true);
      setTimeout(() => router.push(`/${locale}/dashboard`), 2500);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message ?? "招待の承認に失敗しました");
    } finally {
      setAccepting(false);
    }
  }

  const emailMismatch =
    inviteInfo && currentEmail && inviteInfo.invited_email.toLowerCase() !== currentEmail.toLowerCase();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg mb-3">
            <Users className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black text-gray-900">チームへの招待</h1>
          <p className="text-sm text-gray-500 mt-1">EditClone</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
            </div>
          ) : error && !inviteInfo ? (
            /* 招待が無効 */
            <div className="text-center py-4">
              <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
              <p className="font-semibold text-gray-900 mb-1">招待を確認できませんでした</p>
              <p className="text-sm text-gray-500">{error}</p>
              <Link
                href={`/${locale}/dashboard`}
                className="mt-5 inline-block text-sm text-purple-600 underline"
              >
                ダッシュボードへ
              </Link>
            </div>
          ) : accepted ? (
            /* 承認完了 */
            <div className="text-center py-4">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <p className="font-bold text-gray-900 text-lg mb-1">参加しました！</p>
              <p className="text-sm text-gray-500">ダッシュボードへリダイレクトします...</p>
            </div>
          ) : inviteInfo?.status === "accepted" ? (
            /* すでに承認済み */
            <div className="text-center py-4">
              <CheckCircle className="w-12 h-12 text-blue-400 mx-auto mb-3" />
              <p className="font-semibold text-gray-900 mb-1">すでに参加済みです</p>
              <Link
                href={`/${locale}/dashboard`}
                className="mt-3 inline-block text-sm text-purple-600 underline"
              >
                ダッシュボードへ
              </Link>
            </div>
          ) : inviteInfo ? (
            /* 招待詳細・承認フォーム */
            <div className="space-y-5">
              <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                <p className="text-xs text-purple-500 font-medium mb-1">招待先メールアドレス</p>
                <p className="font-bold text-gray-900">{inviteInfo.invited_email}</p>
                <div className="flex items-center gap-1.5 mt-2">
                  <Shield className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-sm text-purple-700">
                    役割: <span className="font-semibold">{ROLE_LABELS[inviteInfo.role] ?? inviteInfo.role}</span>
                  </span>
                </div>
              </div>

              {!currentEmail ? (
                /* 未ログイン */
                <div className="text-center space-y-3">
                  <p className="text-sm text-gray-600">
                    招待を承認するにはログインが必要です。
                  </p>
                  <Link
                    href={`/${locale}/login?next=/teams/invite/${token}`}
                    className="flex items-center justify-center gap-2 w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-xl transition-colors"
                  >
                    <LogIn className="w-4 h-4" />
                    ログインして承認
                  </Link>
                  <Link
                    href={`/${locale}/signup?next=/teams/invite/${token}`}
                    className="block text-sm text-purple-600 hover:text-purple-700 underline"
                  >
                    アカウントをお持ちでない方はこちら
                  </Link>
                </div>
              ) : emailMismatch ? (
                /* メールアドレス不一致 */
                <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                  <p className="text-sm text-red-600 font-medium mb-1">メールアドレスが一致しません</p>
                  <p className="text-xs text-red-500">
                    招待は <strong>{inviteInfo.invited_email}</strong> 宛ですが、
                    現在 <strong>{currentEmail}</strong> でログインしています。
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    招待されたメールアドレスでログインし直してください。
                  </p>
                </div>
              ) : (
                /* 承認ボタン */
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 text-center">
                    <strong>{currentEmail}</strong> でチームに参加します。
                  </p>
                  {error && (
                    <p className="text-xs text-red-500 text-center">{error}</p>
                  )}
                  <button
                    onClick={handleAccept}
                    disabled={accepting}
                    className="flex items-center justify-center gap-2 w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
                  >
                    {accepting ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> 承認中...</>
                    ) : (
                      <><ArrowRight className="w-4 h-4" /> 招待を承認する</>
                    )}
                  </button>
                  <Link
                    href={`/${locale}/dashboard`}
                    className="block text-center text-sm text-gray-400 hover:text-gray-600 underline"
                  >
                    キャンセル
                  </Link>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
