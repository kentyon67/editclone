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
 * FCP Extension: WKWebView から Swift へ FCPXML インポートを依頼する
 */
export function importToFCP(downloadUrl: string, filename: string) {
  const wk = (window as unknown as { webkit?: { messageHandlers?: { editclone?: { postMessage: (m: unknown) => void } } } }).webkit;
  if (wk?.messageHandlers?.editclone) {
    wk.messageHandlers.editclone.postMessage({
      action: "importFCPXML",
      url: downloadUrl,
      filename,
    });
    return true;
  }
  return false;
}

/**
 * Premiere CEP: iframe postMessage で CEP パネルに FCPXML インポートを依頼する
 */
export function importToPremiere(downloadUrl: string, filename: string) {
  window.parent.postMessage(
    { action: "importFCPXML", url: downloadUrl, filename },
    "*"
  );
}

/**
 * DaVinci: ZIP ダウンロード URL をクリップボードにコピーして通知する
 * (DaVinci Script 側が API をポーリングするため、URLは不要。ZIPを開くだけでよい)
 */
export function importToDaVinci(downloadUrl: string) {
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = "editclone_project.zip";
  a.click();
}
