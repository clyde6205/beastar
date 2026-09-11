/**
 * BeAstar mobile — API client
 * ==============================
 * Thin wrapper around the FastAPI backend (see /app/main.py). One function
 * per endpoint, typed request/response shapes matching the backend's
 * Pydantic models exactly, so a backend field rename shows up as a
 * TypeScript error here instead of a silent runtime bug.
 */

import axios, { AxiosInstance } from 'axios';
import * as SecureStore from 'expo-secure-store';

// Point this at your deployed API. Never hardcode a production URL in a
// committed file long-term — pull from an env config (expo-constants +
// app.config.js) once you have separate dev/staging/prod backends.
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// ---------------------------------------------------------------------------
// Types — mirror the Pydantic models in app/main.py
// ---------------------------------------------------------------------------

export type Tier = 'free' | 'star' | 'superstar' | 'megastar';
export type Resolution = '720p' | '1080p' | '4k';
export type JobStatus = 'queued' | 'rendering' | 'complete' | 'failed';

export interface SignupRequest {
  email: string;
  display_name: string;
  date_of_birth: string; // ISO date, e.g. '2005-03-14'
  country_code: string; // ISO 3166-1 alpha-2, e.g. 'PH'
  referral_code_used?: string;
}

export interface SignupResponse {
  user_id: string;
  referral_code: string;
  credits: number;
  requires_face_verification: boolean;
}

export interface GenerationRequest {
  user_id: string;
  scenario_slug: string;
  requested_resolution: Resolution;
  image_url: string;
}

export interface GenerationResponse {
  job_id: string;
  status: JobStatus;
  resolution: Resolution;
  ai_label_included: boolean;
}

export interface LeaderboardEntry {
  user_id: string;
  display_name: string;
  country_code: string;
  videos_created: number;
  successful_referrals: number;
}

export interface Challenge {
  id: string;
  hashtag: string;
  scope: 'global' | 'regional';
  country_code?: string;
  title: string;
  starts_at: string;
  ends_at: string;
  prize_description?: string;
}

export interface GCashCheckoutResponse {
  source_id: string;
  checkout_url: string;
  amount_php: number;
}

export interface DreamThread {
  id: string;
  user_id: string;
  goal_title: string;
  goal_description?: string;
  starting_generation_job_id?: string;
  self_reported_net_worth?: string;
  is_active: boolean;
  created_at: string;
  display_note: string;
  update_count?: number;
  follower_count?: number;
  updates?: DreamUpdate[];
}

export interface DreamUpdate {
  id: string;
  thread_id: string;
  user_id: string;
  caption: string;
  video_url?: string;
  moderation_status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface Encouragement {
  id: string;
  update_id: string;
  user_id: string;
  message?: string;
  created_at: string;
}

export const NET_WORTH_BAND_LABELS: Record<string, string> = {
  under_100k: 'Under $100K',
  '100k_1m': '$100K–$1M',
  '1m_5m': '$1M–$5M',
  '5m_plus': '$5M+',
  prefer_not_to_say: 'Prefer not to say',
};

// ---------------------------------------------------------------------------
// Local session storage — user_id is the only "session token" this backend
// issues right now. Swap for a real JWT/session cookie once auth hardens
// beyond the MVP shape in app/main.py.
// ---------------------------------------------------------------------------

const USER_ID_KEY = 'beastar_user_id';

export async function saveSession(userId: string): Promise<void> {
  await SecureStore.setItemAsync(USER_ID_KEY, userId);
}

export async function getSavedUserId(): Promise<string | null> {
  return SecureStore.getItemAsync(USER_ID_KEY);
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(USER_ID_KEY);
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function signup(req: SignupRequest): Promise<SignupResponse> {
  const { data } = await client.post<SignupResponse>('/auth/signup', req);
  await saveSession(data.user_id);
  return data;
}

export async function verifyFace(userId: string): Promise<{ user_id: string; is_verified: boolean }> {
  const { data } = await client.post(`/auth/${userId}/verify-face`);
  return data;
}

// ---------------------------------------------------------------------------
// Selfie upload
// ---------------------------------------------------------------------------

/**
 * `localUri` is the file:// URI from expo-image-picker or expo-camera.
 * Uploads as multipart/form-data to match the backend's UploadFile param.
 */
export async function uploadSelfie(userId: string, localUri: string, mimeType: string): Promise<{ image_url: string }> {
  const form = new FormData();
  const filename = localUri.split('/').pop() ?? 'selfie.jpg';
  // React Native's FormData accepts this shape for file uploads; the `as any`
  // is unfortunately necessary because RN's FormData typing doesn't fully
  // match the web File API.
  form.append('file', { uri: localUri, name: filename, type: mimeType } as any);

  const { data } = await client.post(`/users/${userId}/uploads/selfie`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------

export async function requestGeneration(req: GenerationRequest): Promise<GenerationResponse> {
  const { data } = await client.post<GenerationResponse>('/generate', req);
  return data;
}

export async function getJobStatus(jobId: string): Promise<{ id: string; status: JobStatus; output_url?: string }> {
  const { data } = await client.get(`/jobs/${jobId}`);
  return data;
}

/**
 * Polls a generation job until it's complete or failed. Intended for the
 * "your star moment is being created" screen. Stops polling and throws
 * after maxAttempts so the UI can show a "taking longer than usual"
 * fallback instead of spinning forever.
 */
export async function pollJobUntilDone(
  jobId: string,
  { intervalMs = 3000, maxAttempts = 60 }: { intervalMs?: number; maxAttempts?: number } = {}
): Promise<{ id: string; status: JobStatus; output_url?: string }> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const job = await getJobStatus(jobId);
    if (job.status === 'complete' || job.status === 'failed') {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error('Generation is taking longer than expected.');
}

// ---------------------------------------------------------------------------
// Sharing / QR
// ---------------------------------------------------------------------------

export function referralQrUrl(userId: string): string {
  // Backend returns a PNG directly — used as an <Image source={{ uri }}> in
  // ShareScreen rather than fetched and decoded manually.
  return `${API_BASE_URL}/qr/${userId}`;
}

// ---------------------------------------------------------------------------
// Leaderboard & challenges
// ---------------------------------------------------------------------------

export async function getLeaderboard(countryCode?: string): Promise<LeaderboardEntry[]> {
  const { data } = await client.get<LeaderboardEntry[]>('/leaderboard', {
    params: countryCode ? { country_code: countryCode } : {},
  });
  return data;
}

export async function getActiveChallenges(countryCode?: string): Promise<Challenge[]> {
  const { data } = await client.get<Challenge[]>('/challenges', {
    params: countryCode ? { country_code: countryCode } : {},
  });
  return data;
}

export async function submitChallengeEntry(
  challengeId: string,
  userId: string,
  generationJobId: string
): Promise<{ id: string }> {
  const { data } = await client.post(`/challenges/${challengeId}/entries`, {
    user_id: userId,
    generation_job_id: generationJobId,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Payments (GCash via PayMongo)
// ---------------------------------------------------------------------------

export async function startGcashCheckout(userId: string, tier: Tier): Promise<GCashCheckoutResponse> {
  const { data } = await client.post<GCashCheckoutResponse>('/payments/gcash/checkout', {
    user_id: userId,
    tier,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Dream threads — the progress-story feature
// ---------------------------------------------------------------------------

export async function createDreamThread(params: {
  user_id: string;
  goal_title: string;
  goal_description?: string;
  starting_generation_job_id?: string;
  self_reported_net_worth?: string;
}): Promise<DreamThread> {
  const { data } = await client.post<DreamThread>('/dream-threads', params);
  return data;
}

export async function getDreamThread(threadId: string): Promise<DreamThread> {
  const { data } = await client.get<DreamThread>(`/dream-threads/${threadId}`);
  return data;
}

export async function getUserDreamThreads(userId: string): Promise<DreamThread[]> {
  const { data } = await client.get<DreamThread[]>(`/users/${userId}/dream-threads`);
  return data;
}

export async function postDreamUpdate(
  threadId: string,
  userId: string,
  caption: string,
  videoUrl?: string
): Promise<DreamUpdate> {
  const { data } = await client.post<DreamUpdate>(`/dream-threads/${threadId}/updates`, {
    user_id: userId,
    caption,
    video_url: videoUrl,
  });
  return data;
}

export async function followDreamThread(threadId: string, followerUserId: string): Promise<void> {
  await client.post(`/dream-threads/${threadId}/follow`, null, {
    params: { follower_user_id: followerUserId },
  });
}

export async function unfollowDreamThread(threadId: string, followerUserId: string): Promise<void> {
  await client.delete(`/dream-threads/${threadId}/follow`, {
    params: { follower_user_id: followerUserId },
  });
}

export async function getFollowedDreamFeed(userId: string): Promise<DreamUpdate[]> {
  const { data } = await client.get<DreamUpdate[]>(`/users/${userId}/dream-feed`);
  return data;
}

export async function addEncouragement(
  updateId: string,
  userId: string,
  message?: string
): Promise<Encouragement> {
  const { data } = await client.post<Encouragement>(`/dream-updates/${updateId}/encouragements`, {
    user_id: userId,
    message,
  });
  return data;
}

export async function getEncouragements(updateId: string): Promise<Encouragement[]> {
  const { data } = await client.get<Encouragement[]>(`/dream-updates/${updateId}/encouragements`);
  return data;
}

export default client;
