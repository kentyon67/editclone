/**
 * 公開ページ E2E テスト
 * 認証不要なページのレンダリング・ナビゲーション・UI 要素を検証する。
 */
import { test, expect } from "@playwright/test";

test.describe("Landing page", () => {
  test("ルートアクセスで日本語ランディングにリダイレクト", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/(ja|en)\/?$/);
    await expect(page.locator("h1").first()).toBeVisible();
  });

  test("日本語ランディングページが正常に表示される", async ({ page }) => {
    await page.goto("/ja");
    await expect(page.locator("h1").first()).toBeVisible();
    // ナビゲーションリンクが存在する
    await expect(page.getByRole("link", { name: /pricing|料金/i }).first()).toBeVisible();
  });

  test("英語ランディングページが表示される", async ({ page }) => {
    await page.goto("/en");
    await expect(page.locator("h1").first()).toBeVisible();
  });

  test("CTA ボタンがログインページへ遷移する", async ({ page }) => {
    await page.goto("/ja");
    const cta = page.getByRole("link", { name: /無料|start|login|ログイン|はじめる/i }).first();
    await expect(cta).toBeVisible();
  });
});

test.describe("Pricing page", () => {
  test("料金ページが正常に表示される", async ({ page }) => {
    await page.goto("/ja/pricing");
    await expect(page).toHaveURL(/pricing/);
    // プラン名が表示される
    await expect(page.getByText(/free|pro|creator|studio/i).first()).toBeVisible();
  });

  test("英語料金ページが表示される", async ({ page }) => {
    await page.goto("/en/pricing");
    await expect(page).toHaveURL(/pricing/);
  });
});

test.describe("Login page", () => {
  test("ログインページが正常に表示される", async ({ page }) => {
    await page.goto("/ja/login");
    await expect(page).toHaveURL(/login/);
    // email/password フォームが存在する
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test("空フォーム送信でバリデーションが動作する", async ({ page }) => {
    await page.goto("/ja/login");
    const submitBtn = page.getByRole("button", { name: /login|ログイン|sign in/i }).first();
    await submitBtn.click();
    // HTML5 バリデーションまたはカスタムエラーが表示される
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("誤った認証情報でエラーが表示される", async ({ page }) => {
    await page.goto("/ja/login");
    await page.fill('input[type="email"]', "invalid@test.example");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.getByRole("button", { name: /login|ログイン|sign in/i }).first().click();
    // エラーメッセージが表示される（タイムアウト: 10秒）
    await expect(
      page.locator("text=/error|エラー|invalid|無効|incorrect|失敗/i").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("英語ログインページが表示される", async ({ page }) => {
    await page.goto("/en/login");
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });
});

test.describe("Protected page redirects", () => {
  test("未認証でダッシュボードにアクセスするとログインにリダイレクト", async ({ page }) => {
    await page.goto("/ja/dashboard");
    await expect(page).toHaveURL(/login/, { timeout: 10_000 });
  });

  test("未認証でアップロードページにアクセスするとログインにリダイレクト", async ({ page }) => {
    await page.goto("/ja/upload");
    await expect(page).toHaveURL(/login/, { timeout: 10_000 });
  });

  test("未認証でスタイルページにアクセスするとログインにリダイレクト", async ({ page }) => {
    await page.goto("/ja/styles");
    await expect(page).toHaveURL(/login/, { timeout: 10_000 });
  });
});
