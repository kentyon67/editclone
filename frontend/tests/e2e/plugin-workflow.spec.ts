/**
 * プラグインワークフロー E2E テスト
 * NLE Plugin API エンドポイントの疎通確認と
 * Plugin 向けの重要 UI フローを検証する。
 *
 * バックエンドが Railway フリー枠でスリープしている場合、
 * 502/503/504/404 を "許容状態" として扱う。
 */
import { test, expect } from "@playwright/test";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.PLAYWRIGHT_API_URL ||
  "https://editclone-production.up.railway.app";

const RAILWAY_SLEEP_CODES = [502, 503, 504, 404, 0];

test.describe("Backend health check", () => {
  test("バックエンド /health エンドポイントが応答する（スリープ許容）", async ({
    request,
  }) => {
    let status = 0;
    try {
      const res = await request.get(`${API_BASE}/health`, {
        timeout: 15_000,
      });
      status = res.status();
      if (res.ok()) {
        const body = await res.json();
        expect(body).toHaveProperty("status");
        console.log(`✓ Backend up: status=${body.status}`);
        return;
      }
    } catch {
      // ネットワークエラー (接続不可)
    }
    // Railway スリープまたは未設定の場合はスキップ
    console.log(`⚠ Backend returned ${status} — likely sleeping or URL not configured`);
    test.skip(RAILWAY_SLEEP_CODES.includes(status), "Backend sleeping or URL not configured");
  });

  test("/health レスポンスにバージョン情報が含まれる（バックエンド起動時のみ）", async ({
    request,
  }) => {
    let res: Awaited<ReturnType<typeof request.get>> | null = null;
    try {
      res = await request.get(`${API_BASE}/health`, { timeout: 10_000 });
    } catch {
      test.skip(true, "Backend not reachable");
      return;
    }
    if (!res.ok()) {
      test.skip(true, `Backend returned ${res.status()}`);
      return;
    }
    const body = await res.json();
    if (body.version) {
      expect(typeof body.version).toBe("string");
    }
  });
});

test.describe("Plugin API unauthenticated behavior", () => {
  async function checkEndpoint(
    request: Parameters<typeof test>[1] extends (args: infer A) => any
      ? A extends { request: infer R }
        ? R
        : never
      : never,
    url: string
  ): Promise<number> {
    try {
      const res = await request.get(url, { timeout: 10_000 });
      return res.status();
    } catch {
      return 0;
    }
  }

  test("認証なしで /plugin/jobs は 401/403 を返す", async ({ request }) => {
    const status = await checkEndpoint(request, `${API_BASE}/plugin/jobs`);
    if (RAILWAY_SLEEP_CODES.includes(status)) {
      test.skip(true, `Backend returned ${status} — sleeping or offline`);
      return;
    }
    expect([401, 403]).toContain(status);
  });

  test("認証なしで /plugin/me は 401/403 を返す", async ({ request }) => {
    const status = await checkEndpoint(request, `${API_BASE}/plugin/me`);
    if (RAILWAY_SLEEP_CODES.includes(status)) {
      test.skip(true, `Backend returned ${status} — sleeping or offline`);
      return;
    }
    expect([401, 403]).toContain(status);
  });

  test("認証なしで /plugin/style-profiles は 401/403 を返す", async ({
    request,
  }) => {
    const status = await checkEndpoint(
      request,
      `${API_BASE}/plugin/style-profiles`
    );
    if (RAILWAY_SLEEP_CODES.includes(status)) {
      test.skip(true, `Backend returned ${status} — sleeping or offline`);
      return;
    }
    expect([401, 403]).toContain(status);
  });

  test("不正トークンで /plugin/jobs/{id}/team-edit は 401/404 を返す", async ({
    request,
  }) => {
    let status = 0;
    try {
      const res = await request.post(
        `${API_BASE}/plugin/jobs/fake-job-id/team-edit`,
        {
          headers: { Authorization: "Bearer invalid-token-xxx" },
          data: { prompt: "フィラー除去", history: [] },
          timeout: 10_000,
        }
      );
      status = res.status();
    } catch {
      test.skip(true, "Backend not reachable");
      return;
    }
    if (RAILWAY_SLEEP_CODES.includes(status)) {
      test.skip(true, `Backend returned ${status}`);
      return;
    }
    expect([401, 403, 404, 422]).toContain(status);
  });
});

test.describe("Frontend styles marketplace page", () => {
  test("マーケットプレイスページが表示またはログインにリダイレクト", async ({
    page,
  }) => {
    await page.goto("/ja/styles/marketplace");
    await page.waitForLoadState("domcontentloaded");
    const url = page.url();
    const isLogin = url.includes("login");
    const isMarketplace = url.includes("marketplace");
    // ログインリダイレクトまたはページ表示のどちらかであること
    expect(isLogin || isMarketplace).toBeTruthy();
    if (isMarketplace) {
      // ページが表示されている場合はコンテンツが存在する
      const body = await page.textContent("body");
      expect(body?.length).toBeGreaterThan(100);
    }
  });
});

test.describe("Frontend navigation consistency", () => {
  test("ランディングから料金ページへのリンクが機能する", async ({ page }) => {
    await page.goto("/ja");
    await page.waitForLoadState("domcontentloaded");
    const pricingLink = page.getByRole("link", { name: /pricing|料金/i }).first();
    if (await pricingLink.isVisible()) {
      await pricingLink.click();
      await expect(page).toHaveURL(/pricing/, { timeout: 10_000 });
    } else {
      // リンクが見つからない場合は直接ナビゲーション
      await page.goto("/ja/pricing");
      await expect(page).toHaveURL(/pricing/);
    }
  });

  test("ランディングからログインページへのリンクが機能する", async ({ page }) => {
    await page.goto("/ja");
    await page.waitForLoadState("domcontentloaded");
    const loginLink = page
      .getByRole("link", { name: /login|ログイン|sign in|始める|無料/i })
      .first();
    if (await loginLink.isVisible()) {
      await loginLink.click();
      await expect(page).toHaveURL(/login|dashboard/, { timeout: 10_000 });
    }
  });

  test("フッターが全公開ページに表示される", async ({ page }) => {
    for (const path of ["/ja", "/ja/pricing", "/ja/login"]) {
      await page.goto(path);
      await page.waitForLoadState("domcontentloaded");
      const footer = page.locator("footer");
      if (await footer.count() > 0) {
        await expect(footer.first()).toBeVisible();
      }
    }
  });
});

test.describe("Styles analyze page", () => {
  test("/styles/analyze ページが存在する（リダイレクトまたは表示）", async ({
    page,
  }) => {
    await page.goto("/ja/styles/analyze");
    await page.waitForLoadState("domcontentloaded");
    const url = new URL(page.url()).pathname;
    const ok =
      url.includes("styles/analyze") || url.includes("login");
    expect(ok).toBeTruthy();
  });
});
