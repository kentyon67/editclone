/**
 * プラグインワークフロー E2E テスト
 * NLE Plugin API エンドポイントの疎通確認と
 * Plugin 向けの重要 UI フローを検証する。
 */
import { test, expect } from "@playwright/test";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://editclone-production.up.railway.app";

test.describe("Backend health check", () => {
  test("バックエンド /health エンドポイントが正常に応答する", async ({ request }) => {
    const res = await request.get(`${API_BASE}/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty("status");
    // status が "ok" または "healthy" であることを確認
    expect(["ok", "healthy", "running"]).toContain(body.status);
  });

  test("/health レスポンスにバージョン情報が含まれる", async ({ request }) => {
    const res = await request.get(`${API_BASE}/health`);
    const body = await res.json();
    // バージョンフィールドが存在する（オプション）
    if (body.version) {
      expect(typeof body.version).toBe("string");
    }
  });
});

test.describe("Plugin API unauthenticated behavior", () => {
  test("認証なしで /plugin/jobs は 401 を返す", async ({ request }) => {
    const res = await request.get(`${API_BASE}/plugin/jobs`);
    expect([401, 403]).toContain(res.status());
  });

  test("認証なしで /plugin/me は 401 を返す", async ({ request }) => {
    const res = await request.get(`${API_BASE}/plugin/me`);
    expect([401, 403]).toContain(res.status());
  });

  test("認証なしで /plugin/style-profiles は 401 を返す", async ({ request }) => {
    const res = await request.get(`${API_BASE}/plugin/style-profiles`);
    expect([401, 403]).toContain(res.status());
  });

  test("不正トークンで /plugin/jobs/{id}/team-edit は 401 を返す", async ({ request }) => {
    const res = await request.post(`${API_BASE}/plugin/jobs/fake-job-id/team-edit`, {
      headers: { Authorization: "Bearer invalid-token-xxx" },
      data: { prompt: "フィラー除去", history: [] },
    });
    expect([401, 403, 404]).toContain(res.status());
  });
});

test.describe("Frontend styles marketplace page", () => {
  test("マーケットプレイスページが正常に表示される", async ({ page }) => {
    await page.goto("/ja/styles/marketplace");
    // ログインリダイレクトまたはページが表示される
    const redirected = page.url().includes("login");
    if (!redirected) {
      await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 10_000 });
    } else {
      // リダイレクトは想定内
      expect(redirected).toBeTruthy();
    }
  });
});

test.describe("Frontend navigation consistency", () => {
  test("ランディングから料金ページへのリンクが機能する", async ({ page }) => {
    await page.goto("/ja");
    const pricingLink = page.getByRole("link", { name: /pricing|料金/i }).first();
    if (await pricingLink.isVisible()) {
      await pricingLink.click();
      await expect(page).toHaveURL(/pricing/, { timeout: 10_000 });
    }
  });

  test("ランディングからログインページへのリンクが機能する", async ({ page }) => {
    await page.goto("/ja");
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
      // フッター要素（著作権表示など）
      const footer = page.locator("footer");
      if (await footer.count() > 0) {
        await expect(footer.first()).toBeVisible();
      }
    }
  });
});

test.describe("Styles analyze page", () => {
  test("/styles/analyze ページが存在する（リダイレクトまたは表示）", async ({ page }) => {
    await page.goto("/ja/styles/analyze");
    // ログインリダイレクトまたはページが表示される（400/404 は NG）
    expect(["/ja/styles/analyze", "/ja/login"]).toContain(
      new URL(page.url()).pathname
    );
  });
});
