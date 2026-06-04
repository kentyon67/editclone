const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadVideo(file: File): Promise<{ video_id: string; filename: string; size_bytes: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/videos/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function startProcessing(
  videoId: string,
  options: { noise_db?: number; min_duration?: number } = {}
): Promise<{ job_id: string; video_id: string; status: string }> {
  const params = new URLSearchParams();
  if (options.noise_db !== undefined) params.set("noise_db", String(options.noise_db));
  if (options.min_duration !== undefined) params.set("min_duration", String(options.min_duration));

  const res = await fetch(`${API_URL}/videos/process/${videoId}?${params}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Processing start failed");
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Job fetch failed");
  }
  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/download`;
}

export interface JobStatusResponse {
  job_id: string;
  video_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: string;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  result?: {
    info: Record<string, unknown>;
    transcript: { language: string; segments: Segment[]; transcript: string };
    cuts: Cut[];
    chapters: Chapter[];
    youtube_description: string;
    srt: string;
  };
}

export interface Segment {
  start: number;
  end: number;
  text: string;
}

export interface Cut {
  cut_start: number;
  cut_end: number;
  duration: number;
  reason: string;
}

export interface Chapter {
  start_seconds: number;
  start_formatted: string;
  title: string;
}

async function authHeaders(): Promise<Record<string, string>> {
  try {
    const { createClient } = await import("./supabase");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export async function createCheckout(
  plan: "pro" | "creator" | "studio",
  successUrl: string,
  cancelUrl: string
): Promise<{ checkout_url: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/billing/create-checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ plan, success_url: successUrl, cancel_url: cancelUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Checkout failed");
  }
  return res.json();
}

export async function getBillingPortal(returnUrl: string): Promise<{ portal_url: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/billing/portal?return_url=${encodeURIComponent(returnUrl)}`, {
    headers,
  });
  if (!res.ok) throw new Error("Portal fetch failed");
  return res.json();
}
