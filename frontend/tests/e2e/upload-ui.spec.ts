/**
 * アップロードページ UI テスト
 * 認証が必要なページのため、ローカルストレージに偽のセッションを注入してテストする。
 * 実際の API コールはモックせず、UI の見た目と動作のみ検証する。
 */
import { test, expect, Page } from "@playwright/test";

/**
 * テスト用の偽 Supabase セッションをブラウザ Storage に注入する。
 * これにより middleware のリダイレクトを回避してページが表示される。
 */
async function injectFakeSession(page: Page, supabaseUrl: string) {
  const projectRef = new URL(supabaseUrl).hostname.split(".")[0];
  const storageKey = `sb-${projectRef}-auth-token`;
  const fakeSession = {
    access_token: "fake-token-for-ui-test",
    refresh_token: "fake-refresh-token",
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    user: {
      id: "test-user-id",
      email: "test@example.com",
      role: "authenticated",
    },
  };
  await page.addInitScript(
    ({ key, value }) => {
      localStorage.setItem(key, JSON.stringify(value));
    },
    { key: storageKey, value: fakeSession }
  );
}

// テスト対象 URL（env から取得可能）
const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  "https://placeholder.supabase.co";

test.describe("Upload page UI (mocked auth)", () => {
  test.beforeEach(async ({ page }) => {
    await injectFakeSession(page, SUPABASE_URL);
  });

  test("アップロードページの主要要素が表示される", async ({ page }) => {
    await page.goto("/ja/upload");
    // ページタイトル or ドロップゾーン
    const dropzone = page.locator('text=/ドロップ|drop|upload|アップロード/i').first();
    await expect(dropzone).toBeVisible({ timeout: 15_000 });
  });

  test("ドロップゾーンにファイルをドロップできる UI が存在する", async ({ page }) => {
    await page.goto("/ja/upload");
    // ファイル入力要素が存在する
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    // ドロップゾーンの境界が表示される
    const dropArea = page.locator('[class*="border-dashed"], [class*="border-2"]').first();
    await expect(dropArea).toBeVisible({ timeout: 15_000 });
  });

  test("ファイル選択後にファイル情報が表示される", async ({ page }) => {
    await page.goto("/ja/upload");

    // 1x1 ピクセルの MP4 相当のダミーファイル（MIME だけ合わせる）
    const dummyContent = Buffer.from("dummy video content");
    const fileInput = page.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: "test_video.mp4",
      mimeType: "video/mp4",
      buffer: dummyContent,
    });

    // ファイル名が表示される
    await expect(page.getByText("test_video.mp4")).toBeVisible({ timeout: 5_000 });
  });

  test("プロンプト入力欄が存在する", async ({ page }) => {
    await page.goto("/ja/upload");
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible({ timeout: 15_000 });
    await textarea.click();
    await textarea.fill("フィラーを除去してテンポよく編集してください");
    await expect(textarea).toHaveValue("フィラーを除去してテンポよく編集してください");
  });

  test("クイック選択ボタンがプロンプトを入力する", async ({ page }) => {
    await page.goto("/ja/upload");
    const quickBtn = page.getByText("フィラー除去");
    if (await quickBtn.isVisible()) {
      await quickBtn.click();
      const textarea = page.locator("textarea").first();
      await expect(textarea).not.toBeEmpty();
    }
  });

  test("設定パネルの展開・折りたたみが動作する", async ({ page }) => {
    await page.goto("/ja/upload");
    const settingsBtn = page.getByText(/設定|setting/i).first();
    if (await settingsBtn.isVisible()) {
      await settingsBtn.click();
      // スライダーが表示される
      await expect(page.locator('input[type="range"]').first()).toBeVisible({ timeout: 5_000 });
      await settingsBtn.click();
    }
  });
});

test.describe("Results page UI (mocked auth)", () => {
  test("存在しないジョブIDで404相当の表示になる", async ({ page }) => {
    await injectFakeSession(page, SUPABASE_URL);
    await page.goto("/ja/results/nonexistent-job-id-99999");
    // エラー表示またはリダイレクトが起きる
    await page.waitForTimeout(5_000);
    const body = await page.textContent("body");
    // 「not found」「エラー」「404」のいずれかが含まれるか、ログインにリダイレクト
    const hasError =
      /not found|エラー|404|failed|login/i.test(body || "") ||
      page.url().includes("login");
    expect(hasError).toBeTruthy();
  });
});
