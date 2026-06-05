"use client";

export type PluginNLE = "fcp" | "premiere" | "davinci" | null;

const STORAGE_KEY = "editclone_plugin_nle";

export function setPluginMode(nle: PluginNLE) {
  if (typeof window === "undefined") return;
  if (nle) {
    sessionStorage.setItem(STORAGE_KEY, nle);
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

export function getPluginMode(): PluginNLE {
  if (typeof window === "undefined") return null;
  return (sessionStorage.getItem(STORAGE_KEY) as PluginNLE) ?? null;
}

export const NLE_LABELS: Record<NonNullable<PluginNLE>, { name: string; importLabel: string; color: string }> = {
  fcp: {
    name: "Final Cut Pro",
    importLabel: "Final Cut Proにインポート",
    color: "from-gray-700 to-gray-900",
  },
  premiere: {
    name: "Premiere Pro",
    importLabel: "Premiere Proにインポート",
    color: "from-violet-700 to-purple-900",
  },
  davinci: {
    name: "DaVinci Resolve",
    importLabel: "DaVinci Resolveにインポート",
    color: "from-orange-600 to-red-700",
  },
};

/**
 * FCP Extension: WKWebView から Swift へ FCPXML インポートを依頼する。
 * jobId + token + apiBase を渡して Swift 側で直接ダウンロードさせる。
 */
export function importToFCP(jobId: string, token: string, apiBase: string): boolean {
  const wk = (window as unknown as {
    webkit?: {
      messageHandlers?: {
        editclone?: { postMessage: (m: unknown) => void }
      }
    }
  }).webkit;

  if (wk?.messageHandlers?.editclone) {
    wk.messageHandlers.editclone.postMessage({
      action: "importFCPXML",
      jobId,
      token,
      apiBase,
    });
    return true;
  }
  return false;
}

/**
 * Premiere CEP: iframe postMessage で CEP パネルに XMEML インポートを依頼する。
 * jobId + token + apiBase を渡して CEP 側で直接 XML ダウンロード → Premiere にインポート。
 */
export function importToPremiere(jobId: string, token: string, apiBase: string) {
  window.parent.postMessage(
    { action: "importPremiereXML", jobId, token, apiBase },
    "*"
  );
}

/**
 * DaVinci: EDL は DaVinci スクリプトが API から取得するため、
 * Web からは ZIP 全体をダウンロードして手動補助として提供する。
 */
export function importToDaVinci(downloadUrl: string) {
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = "editclone_project.zip";
  a.click();
}
