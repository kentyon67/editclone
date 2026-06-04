"use client";
import { useLocale } from "next-intl";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, CreditCard, LogOut, ChevronRight, Film } from "lucide-react";
import Header from "@/components/Header";
import { createClient } from "@/lib/supabase";

const PLANS = [
  { key: "free", name: "Free", price: "¥0", limit: "月3本" },
  { key: "pro", name: "Pro", price: "¥980/月", limit: "月30本" },
  { key: "creator", name: "Creator", price: "¥2,980/月", limit: "月100本" },
  { key: "studio", name: "Studio", price: "¥9,800/月", limit: "無制限" },
];

export default function AccountPage() {
  const locale = useLocale();
  const router = useRouter();
  const [currentPlan] = useState("free");

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push(`/${locale}`);
  }

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
              <p className="text-gray-900 font-medium">user@example.com</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-white" />
              </div>
              <h2 className="font-bold text-gray-900">プラン</h2>
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
                    {plan.key !== currentPlan && (
                      <button className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700 font-medium">
                        変更 <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                    {plan.key === currentPlan && (
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">現在</span>
                    )}
                  </div>
                </div>
              ))}
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
