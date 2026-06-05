export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly code?: string,
    public readonly data?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
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

async function handleError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => ({}));
  const detail = body.detail;
  if (detail && typeof detail === "object") {
    throw new ApiError(
      detail.message ?? fallback,
      res.status,
      detail.code,
      detail as Record<string, unknown>
    );
  }
  throw new ApiError(typeof detail === "string" ? detail : fallback, res.status);
}

export async function uploadVideo(file: File): Promise<{ video_id: string; filename: string; size_bytes: number }> {
  const form = new FormData();
  form.append("file", file);
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/videos/upload`, { method: "POST", headers, body: form });
  if (!res.ok) return handleError(res, "Upload failed");
  return res.json();
}

export async function startProcessing(
  videoId: string,
  options: { noise_db?: number; min_duration?: number; prompt?: string } = {}
): Promise<{ job_id: string; video_id: string; status: string }> {
  const params = new URLSearchParams();
  if (options.noise_db !== undefined) params.set("noise_db", String(options.noise_db));
  if (options.min_duration !== undefined) params.set("min_duration", String(options.min_duration));
  if (options.prompt) params.set("prompt", options.prompt);

  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/videos/process/${videoId}?${params}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) return handleError(res, "Processing start failed");
  return res.json();
}

export function getPremiereXmlUrl(jobId: string): string {
  return `${API_URL}/plugin/jobs/${jobId}/premiere-xml`;
}

export function getFcpxmlUrl(jobId: string): string {
  return `${API_URL}/plugin/jobs/${jobId}/fcpxml`;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`);
  if (!res.ok) return handleError(res, "Job fetch failed");
  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/download`;
}

export function getMp4Url(jobId: string): string {
  return `${API_URL}/jobs/${jobId}/mp4`;
}

export async function getUserJobs(): Promise<{ jobs: UserJob[] }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/jobs`, { headers });
  if (!res.ok) return handleError(res, "Jobs fetch failed");
  return res.json();
}

export async function getUserUsage(): Promise<UsageResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/usage/me`, { headers });
  if (!res.ok) return handleError(res, "Usage fetch failed");
  return res.json();
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
  if (!res.ok) return handleError(res, "Checkout failed");
  return res.json();
}

export async function getBillingPortal(returnUrl: string): Promise<{ portal_url: string }> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_URL}/billing/portal?return_url=${encodeURIComponent(returnUrl)}`,
    { headers }
  );
  if (!res.ok) throw new ApiError("Portal fetch failed", res.status);
  return res.json();
}

export interface UsageResponse {
  plan: string;
  used: number;
  limit: number | null;
  remaining: number | null;
  max_duration_seconds: number | null;
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
    has_mp4: boolean;
    has_subtitles: boolean;
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

export interface StyleProfile {
  id: string;
  user_id: string;
  name: string;
  description: string;
  noise_db: number;
  min_silence_seconds: number;
  default_prompt: string;
  is_active: boolean;
  job_count: number;
  created_at: string;
  updated_at: string;
}

export async function listStyleProfiles(): Promise<{ profiles: StyleProfile[] }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles`, { headers });
  if (!res.ok) return handleError(res, "Style profiles fetch failed");
  return res.json();
}

export async function getActiveStyleProfile(): Promise<{ profile: StyleProfile | null }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/active`, { headers });
  if (!res.ok) return { profile: null };
  return res.json();
}

export async function createStyleProfile(data: {
  name: string;
  description?: string;
  noise_db?: number;
  min_silence_seconds?: number;
  default_prompt?: string;
}): Promise<StyleProfile> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(data),
  });
  if (!res.ok) return handleError(res, "Create style profile failed");
  return res.json();
}

export async function updateStyleProfile(
  id: string,
  data: Partial<{ name: string; description: string; noise_db: number; min_silence_seconds: number; default_prompt: string }>
): Promise<StyleProfile> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(data),
  });
  if (!res.ok) return handleError(res, "Update style profile failed");
  return res.json();
}

export async function deleteStyleProfile(id: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${id}`, { method: "DELETE", headers });
  if (!res.ok) return handleError(res, "Delete style profile failed");
}

export async function activateStyleProfile(id: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${id}/activate`, { method: "POST", headers });
  if (!res.ok) return handleError(res, "Activate style profile failed");
}

export async function postFeedback(data: {
  job_id: string;
  action: "accept" | "reject" | "partial";
  style_profile_id?: string;
  notes?: string;
}): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(data),
  });
  if (!res.ok) return handleError(res, "Feedback post failed");
}

export interface UserJob {
  job_id: string;
  video_filename: string;
  video_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  has_mp4: boolean;
  cut_count: number | null;
}

export interface ReferenceVideo {
  id: string;
  user_id: string;
  style_profile_id: string;
  url: string;
  oembed_title: string | null;
  oembed_thumbnail_url: string | null;
  oembed_provider: string | null;
  created_at: string;
}

export async function listReferenceVideos(profileId: string): Promise<{ videos: ReferenceVideo[] }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/reference-videos`, { headers });
  if (!res.ok) return { videos: [] };
  return res.json();
}

export async function addReferenceVideo(profileId: string, url: string): Promise<ReferenceVideo> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/reference-videos`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) return handleError(res, "Add reference video failed");
  return res.json();
}

export async function deleteReferenceVideo(profileId: string, videoId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/reference-videos/${videoId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) return handleError(res, "Delete reference video failed");
}

export async function aiRefineProfile(profileId: string): Promise<{ suggested_prompt: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/ai-refine`, {
    method: "POST",
    headers,
  });
  if (!res.ok) return handleError(res, "AI refine failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// Projects (Phase 3)
// ---------------------------------------------------------------------------

export interface ProjectRevision {
  id: string;
  project_id: string;
  revision_number: number;
  source: "web" | "plugin";
  notes: string;
  result_path: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  source_job_id: string;
  style_profile_id: string | null;
  sync_status: "local" | "synced" | "conflict";
  created_at: string;
  updated_at: string;
  project_revisions: ProjectRevision[];
}

export async function listProjects(): Promise<{ projects: Project[] }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/projects`, { headers });
  if (!res.ok) return { projects: [] };
  return res.json();
}

export async function getProject(projectId: string): Promise<Project | null> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/projects/${projectId}`, { headers });
  if (!res.ok) return null;
  return res.json();
}

export async function reExportProject(
  projectId: string,
  prompt?: string,
): Promise<{ job_id: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/projects/${projectId}/re-export`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ prompt: prompt ?? null }),
  });
  if (!res.ok) return handleError(res, "Re-export failed");
  return res.json();
}

export async function postPluginRevision(
  projectId: string,
  notes: string = "",
  metadata: Record<string, unknown> = {},
): Promise<{ revision: ProjectRevision; sync_status: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/projects/${projectId}/revisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ notes, metadata }),
  });
  if (!res.ok) return handleError(res, "Plugin revision post failed");
  return res.json();
}
