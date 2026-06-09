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
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/jobs/${jobId}`, { headers });
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
  progress_percent?: number;
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

export interface CaptionStyle {
  font_size: number;
  position: "bottom" | "top" | "middle";
  primary_color: string;
  outline_color: string;
  bold: boolean;
  zoom_effect?: "none" | "subtle" | "punch";
}

export const DEFAULT_CAPTION_STYLE: CaptionStyle = {
  font_size: 28,
  position: "bottom",
  primary_color: "#FFFFFF",
  outline_color: "#000000",
  bold: true,
  zoom_effect: "none",
};

export interface StyleProfile {
  id: string;
  user_id: string;
  name: string;
  description: string;
  noise_db: number;
  min_silence_seconds: number;
  default_prompt: string;
  caption_style: CaptionStyle | null;
  is_active: boolean;
  job_count: number;
  is_public?: boolean;
  public_description?: string;
  copy_count?: number;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export interface PublicStyleProfile extends Omit<StyleProfile, "is_active" | "job_count" | "updated_at"> {
  copy_count: number;
  tags: string[];
}

export async function listMarketplaceProfiles(tag?: string): Promise<{ profiles: PublicStyleProfile[] }> {
  const headers = await authHeaders();
  const url = tag
    ? `${API_URL}/style-profiles/marketplace?tag=${encodeURIComponent(tag)}`
    : `${API_URL}/style-profiles/marketplace`;
  const res = await fetch(url, { headers });
  if (!res.ok) return { profiles: [] };
  return res.json();
}

export async function copyMarketplaceProfile(profileId: string, newName?: string): Promise<StyleProfile> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/marketplace/${profileId}/copy`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ new_name: newName || "" }),
  });
  if (!res.ok) return handleError(res, "Copy profile failed");
  return res.json();
}

export async function publishStyleProfile(profileId: string, publicDescription: string, tags: string[]): Promise<StyleProfile> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ public_description: publicDescription, tags }),
  });
  if (!res.ok) return handleError(res, "Publish profile failed");
  return res.json();
}

export async function unpublishStyleProfile(profileId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/unpublish`, {
    method: "POST",
    headers,
  });
  if (!res.ok) return handleError(res, "Unpublish profile failed");
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
  caption_style?: CaptionStyle;
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
  data: Partial<{ name: string; description: string; noise_db: number; min_silence_seconds: number; default_prompt: string; caption_style: CaptionStyle }>
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

export interface ProfileStats {
  total: number;
  accept: number;
  partial: number;
  reject: number;
}

export async function getProfileStats(profileId: string): Promise<ProfileStats> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/stats`, { headers });
  if (!res.ok) return { total: 0, accept: 0, partial: 0, reject: 0 };
  return res.json();
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

// ---------------------------------------------------------------------------
// Edit DNA — 編集前後ペア分析 (Phase 6)
// ---------------------------------------------------------------------------

export interface EditDnaResult {
  before_duration: number;
  after_duration: number;
  removed_ratio: number;
  removed_seconds: number;
  cuts_per_minute: number;
  avg_segment_seconds: number;
  silence_count: number;
  detected_noise_db: number;
  suggested_noise_db: number;
  suggested_min_silence: number;
  suggested_prompt: string;
}

export async function analyzeEditPair(
  before: File,
  after: File,
): Promise<EditDnaResult> {
  const form = new FormData();
  form.append("before", before);
  form.append("after", after);
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/analyze-pair`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!res.ok) return handleError(res, "Edit pair analysis failed");
  return res.json();
}

export async function applyDnaToProfile(
  profileId: string,
  data: { noise_db: number; min_silence_seconds: number; default_prompt?: string },
): Promise<StyleProfile> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/apply-dna`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(data),
  });
  if (!res.ok) return handleError(res, "Apply DNA failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// Slideshow (Phase 4)
// ---------------------------------------------------------------------------

export async function createSlideshow(
  images: File[],
  options: { duration_per_slide?: number; transition?: string; width?: number; height?: number } = {},
): Promise<Blob> {
  const form = new FormData();
  for (const img of images) form.append("images", img);
  if (options.duration_per_slide !== undefined)
    form.append("duration_per_slide", String(options.duration_per_slide));
  if (options.transition) form.append("transition", options.transition);
  if (options.width) form.append("width", String(options.width));
  if (options.height) form.append("height", String(options.height));

  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/videos/slideshow`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!res.ok) return handleError(res, "Slideshow creation failed");
  return res.blob();
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

// ---------------------------------------------------------------------------
// Web インタラクティブ編集 (refine)
// ---------------------------------------------------------------------------

export interface RefineOperation {
  type: string;
  description?: string;
  keep_segments?: Array<{ start: number; end: number }>;
  [key: string]: unknown;
}

export interface RefineResult {
  job_id: string;
  prompt: string;
  operations: RefineOperation[];
  cuts: Array<{ cut_start: number; cut_end: number; reason: string; source: string }>;
  srt: string;
  fcpxml: string;
  mp4_base64: string | null;
  duration: number;
  fps: number;
  needs_fcpxml_import: boolean;
}

export async function refineJob(
  jobId: string,
  prompt: string,
  returnMp4 = true,
): Promise<RefineResult> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/jobs/${jobId}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ prompt, return_mp4: returnMp4 }),
  });
  if (!res.ok) return handleError(res, "Refine failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// B-roll 提案 (Phase 4)
// ---------------------------------------------------------------------------

export interface BrollSuggestion {
  start: number;
  end: number;
  duration: number;
  keyword: string;
  description: string;
  b_roll_type: string;
  priority: "high" | "medium" | "low";
}

export async function getBrollSuggestions(jobId: string): Promise<{
  job_id: string;
  suggestion_count: number;
  suggestions: BrollSuggestion[];
}> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/jobs/${jobId}/broll-suggestions`, { headers });
  if (!res.ok) return handleError(res, "B-roll suggestions failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// 精度メトリクス (Phase 6-2)
// ---------------------------------------------------------------------------

export interface AccuracyWeek {
  week: string;
  accept: number;
  partial: number;
  reject: number;
  total: number;
  accept_rate: number;
}

export interface ProfileAccuracy {
  profile_id: string;
  total_feedback: number;
  overall_accept_rate: number;
  trend: "improving" | "declining" | "stable";
  weeks: AccuracyWeek[];
}

export async function getProfileAccuracy(profileId: string): Promise<ProfileAccuracy> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/${profileId}/accuracy`, { headers });
  if (!res.ok) return handleError(res, "Accuracy fetch failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// マーケット評価・レビュー (Phase 6-3)
// ---------------------------------------------------------------------------

export interface MarketplaceReview {
  id: string;
  rating: number;
  review_text: string;
  created_at: string;
}

export interface ReviewStats {
  count: number;
  average: number;
  distribution: Record<string, number>;
}

export async function addMarketplaceReview(
  profileId: string,
  rating: number,
  reviewText: string = "",
): Promise<MarketplaceReview> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/marketplace/${profileId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ rating, review_text: reviewText }),
  });
  if (!res.ok) return handleError(res, "Review post failed");
  return res.json();
}

export async function getMarketplaceReviews(profileId: string): Promise<{
  stats: ReviewStats;
  reviews: MarketplaceReview[];
}> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/style-profiles/marketplace/${profileId}/reviews`, { headers });
  if (!res.ok) return { stats: { count: 0, average: 0, distribution: {} }, reviews: [] };
  return res.json();
}

// ---------------------------------------------------------------------------
// チーム管理 (Phase 6-4: Studio プランのみ)
// ---------------------------------------------------------------------------

export interface TeamMember {
  id: string;
  invited_email: string;
  member_id: string | null;
  role: "editor" | "admin";
  status: "pending" | "accepted" | "rejected";
  created_at: string;
}

export async function getTeam(): Promise<{
  my_team: { members: TeamMember[] };
  joined_teams: { id: string; owner_id: string; role: string; status: string; created_at: string }[];
}> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/teams`, { headers });
  if (!res.ok) return handleError(res, "Team fetch failed");
  return res.json();
}

export async function inviteTeamMember(
  email: string,
  role: "editor" | "admin" = "editor",
): Promise<TeamMember> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/teams/invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) return handleError(res, "Invite failed");
  return res.json();
}

export async function removeTeamMember(memberRowId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/teams/members/${memberRowId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) return handleError(res, "Remove member failed");
}

export async function getTeamInviteInfo(token: string): Promise<{
  invited_email: string;
  role: string;
  status: string;
}> {
  const res = await fetch(`${API_URL}/teams/invitations/${token}`);
  if (!res.ok) return handleError(res, "Invite info fetch failed");
  return res.json();
}

export async function acceptTeamInvite(token: string): Promise<{ accepted: boolean; role: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/teams/invitations/${token}/accept`, {
    method: "POST",
    headers,
  });
  if (!res.ok) return handleError(res, "Accept invite failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// 外部APIキー管理 (Phase 6-4: 外部API公開)
// ---------------------------------------------------------------------------

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  revoked: boolean;
  last_used_at: string | null;
  created_at: string;
  raw_key?: string;
}

export async function listApiKeys(): Promise<ApiKey[]> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/api-keys`, { headers });
  if (!res.ok) return [];
  const data = await res.json();
  return data.api_keys ?? [];
}

export async function createApiKey(name: string): Promise<ApiKey> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) return handleError(res, "API key creation failed");
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/api-keys/${keyId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) return handleError(res, "API key revocation failed");
}

// ---------------------------------------------------------------------------
// Webhook管理 (Phase 6-4: Webhook連携)
// ---------------------------------------------------------------------------

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
  secret?: string;
}

export async function listWebhooks(): Promise<Webhook[]> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/webhooks`, { headers });
  if (!res.ok) return [];
  const data = await res.json();
  return data.webhooks ?? [];
}

export async function createWebhook(
  url: string,
  events: string[] = ["job.completed", "job.failed"],
): Promise<Webhook> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/webhooks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ url, events }),
  });
  if (!res.ok) return handleError(res, "Webhook creation failed");
  return res.json();
}

export async function deleteWebhook(webhookId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/webhooks/${webhookId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) return handleError(res, "Webhook deletion failed");
}
