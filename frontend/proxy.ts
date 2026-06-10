import createIntlMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";
import { createMiddlewareClient } from "./lib/supabase-server";

const intlMiddleware = createIntlMiddleware(routing);

const PROTECTED_SEGMENTS = new Set([
  "dashboard",
  "upload",
  "results",
  "styles",
  "account",
  "projects",
  "teams",
]);

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const segments = pathname.split("/");
  const locales = routing.locales as readonly string[];
  const locale = locales.includes(segments[1]) ? segments[1] : routing.defaultLocale;
  const pageSegment = locales.includes(segments[1]) ? segments[2] : segments[1];

  if (PROTECTED_SEGMENTS.has(pageSegment)) {
    const { supabase, response } = createMiddlewareClient(request);
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      const loginUrl = new URL(`/${locale}/login`, request.url);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }

    return response;
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)" ],
};
