import { createServerClient } from "@supabase/ssr";
import createIntlMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const intlMiddleware = createIntlMiddleware(routing);

const PROTECTED = ["/dashboard", "/upload", "/results", "/account"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 保護ルート判定（ロケールプレフィックスを除いたパス）
  const pathnameWithoutLocale = pathname.replace(/^\/(ja|en)/, "") || "/";
  const isProtected = PROTECTED.some((p) => pathnameWithoutLocale.startsWith(p));

  if (isProtected) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    // Supabase未設定（ローカル開発）はそのまま通す
    if (!supabaseUrl || !supabaseKey) {
      return intlMiddleware(request);
    }

    const response = NextResponse.next();
    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    });

    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      const locale = pathname.match(/^\/(ja|en)/)?.[1] ?? "ja";
      return NextResponse.redirect(new URL(`/${locale}/login`, request.url));
    }
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
