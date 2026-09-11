/**
 * BeAstar mobile — API client
 * ==============================
 * Complete production-ready API client for BeAstar backend.
 * One function per endpoint, typed request/response shapes matching the backend's
 * Pydantic models exactly.
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';
import * as FileSystem from 'expo-file-system';
import { Platform } from 'react-native';

// Configuration
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

// Create axios client with interceptors
const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
});

// Request interceptor for adding auth headers
client.interceptors.request.use((config) => {
  // Add any common headers here
  return config;
});

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle network errors
    if (!error.response) {
      error.message = 'Network error. Please check your connection.';
    }
    // Handle server errors
    else if (error.response.status >= 500) {
      error.message = 'Server error. Please try again later.';
    }
    // Handle validation errors
    else if (error.response.status === 422) {
      error.message = 'Validation error. Please check your input.';
    }
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Types — mirror the Pydantic models in backend/app/main.py
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

export interface FaceVerificationRequest {
  selfie_image_url: string;
}

export interface FaceVerificationResponse {
  user_id: string;
  is_verified: boolean;
  face_embedding_id?: string;
  message?: string;
}

export interface SelfieUploadResponse {
  image_url: string;
  content_safety_status: string;
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

export interface JobStatusResponse {
  id: string;
  user_id: string;
  scenario_id?: string;
  resolution: Resolution;
  status: JobStatus;
  provider?: string;
  provider_job_id?: string;
  output_url?: string;
  render_cost_usd?: number;
  credits_charged: number;
  created_at: string;
  completed_at?: string;
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

export interface ChallengeEntry {
  id: string;
  challenge_id: string;
  user_id: string;
  generation_job_id: string;
  vote_count: number;
  submitted_at: string;
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

export interface VoteResponse {
  entry_id: string;
  vote_count: number;
}

export interface PaymentWebhookPayload {
  type: string;
  data: any;
}

export const NET_WORTH_BAND_LABELS: Record<string, string> = {
  under_100k: 'Under $100K',
  '100k_1m': '$100K\u2013$1M',
  '1m_5m': '$1M\u2013$5M',
  '5m_plus': '$5M+',
  prefer_not_to_say: 'Prefer not to say',
};

// ---------------------------------------------------------------------------
// Local session storage
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

export async function verifyFace(
  userId: string,
  selfieImageUrl: string
): Promise<FaceVerificationResponse> {
  const { data } = await client.post<FaceVerificationResponse>(
    `/auth/${userId}/verify-face`,
    { selfie_image_url: selfieImageUrl }
  );
  return data;
}

// ---------------------------------------------------------------------------
// Selfie upload
// ---------------------------------------------------------------------------

/**
 * Uploads a selfie image to the server.
 * 
 * @param userId - The user's ID
 * @param localUri - The file:// URI from expo-image-picker or expo-camera
 * @param onProgress - Optional callback for upload progress (0-100)
 * @returns Promise with the uploaded image URL
 */
export async function uploadSelfie(
  userId: string,
  localUri: string,
  onProgress?: (progress: number) => void
): Promise<SelfieUploadResponse> {
  // Get file info
  const fileInfo = await FileSystem.getInfoAsync(localUri);
  const mimeType = getMimeType(localUri);
  const filename = localUri.split('/').pop() ?? 'selfie.jpg';
  
  // Read the file as base64 for consistent handling across platforms
  const base64 = await FileSystem.readAsStringAsync(localUri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Create FormData
  const form = new FormData();
  
  // Append the file data
  form.append('file', {
    uri: localUri,
    name: filename,
    type: mimeType,
    data: base64,
  } as any);

  // Upload with progress tracking
  const config: AxiosRequestConfig = {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(progress);
      }
    },
  };

  const { data } = await client.post<SelfieUploadResponse>(
    `/users/${userId}/uploads/selfie`,
    form,
    config
  );
  
  return data;
}

/**
 * Uploads a video file to the server for dream updates.
 * 
 * @param userId - The user's ID
 * @param localUri - The file:// URI from expo-image-picker
 * @param onProgress - Optional callback for upload progress (0-100)
 * @returns Promise with the uploaded video URL
 */
export async function uploadVideo(
  userId: string,
  localUri: string,
  onProgress?: (progress: number) => void
): Promise<{ video_url: string }> {
  // Get file info
  const fileInfo = await FileSystem.getInfoAsync(localUri);
  const mimeType = getMimeType(localUri);
  const filename = localUri.split('/').pop() ?? 'update.mp4';
  
  // Read the file as base64
  const base64 = await FileSystem.readAsStringAsync(localUri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Create FormData
  const form = new FormData();
  
  // Append the video data
  form.append('file', {
    uri: localUri,
    name: filename,
    type: mimeType,
    data: base64,
  } as any);

  // Upload with progress tracking
  const config: AxiosRequestConfig = {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(progress);
      }
    },
  };

  // Upload to a dedicated video upload endpoint
  const { data } = await client.post<{ video_url: string }>(
    `/users/${userId}/uploads/video`,
    form,
    config
  );
  
  return data;
}

/**
 * Helper to get MIME type from file extension
 */
function getMimeType(uri: string): string {
  const extension = uri.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'webp':
      return 'image/webp';
    case 'mp4':
      return 'video/mp4';
    default:
      return 'application/octet-stream';
  }
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------

export async function requestGeneration(req: GenerationRequest): Promise<GenerationResponse> {
  const { data } = await client.post<GenerationResponse>('/generate', req);
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const { data } = await client.get<JobStatusResponse>(`/jobs/${jobId}`);
  return data;
}

/**
 * Polls a generation job until it's complete or failed.
 */
export async function pollJobUntilDone(
  jobId: string,
  { intervalMs = 3000, maxAttempts = 120 }: { intervalMs?: number; maxAttempts?: number } = {}
): Promise<JobStatusResponse> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const job = await getJobStatus(jobId);
    if (job.status === 'complete' || job.status === 'failed') {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error('Generation is taking longer than expected. Please try again.');
}

// ---------------------------------------------------------------------------
// Sharing / QR
// ---------------------------------------------------------------------------

export function referralQrUrl(userId: string): string {
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
): Promise<ChallengeEntry> {
  const { data } = await client.post<ChallengeEntry>(
    `/challenges/${challengeId}/entries`,
    { user_id: userId, generation_job_id: generationJobId }
  );
  return data;
}

export async function voteChallengeEntry(
  entryId: string,
  voterUserId: string
): Promise<VoteResponse> {
  const { data } = await client.post<VoteResponse>(
    `/challenges/entries/${entryId}/vote`,
    null,
    { params: { voter_user_id: voterUserId } }
  );
  return data;
}

export async function getChallengeLeaderboard(
  challengeId: string,
  limit = 50
): Promise<ChallengeEntry[]> {
  const { data } = await client.get<ChallengeEntry[]>(
    `/challenges/${challengeId}/leaderboard`,
    { params: { limit } }
  );
  return data;
}

// ---------------------------------------------------------------------------
// Payments (GCash via PayMongo)
// ---------------------------------------------------------------------------

export async function startGcashCheckout(
  userId: string,
  tier: Tier
): Promise<GCashCheckoutResponse> {
  const { data } = await client.post<GCashCheckoutResponse>(
    '/payments/gcash/checkout',
    { user_id: userId, tier }
  );
  return data;
}

// ---------------------------------------------------------------------------
// Dream threads
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
  videoLocalUri?: string
): Promise<DreamUpdate> {
  // If a video is provided, upload it first
  let videoUrl: string | undefined;
  
  if (videoLocalUri) {
    const uploadResult = await uploadVideo(userId, videoLocalUri);
    videoUrl = uploadResult.video_url;
  }
  
  const { data } = await client.post<DreamUpdate>(
    `/dream-threads/${threadId}/updates`,
    { user_id: userId, caption, video_url: videoUrl }
  );
  return data;
}

export async function followDreamThread(
  threadId: string,
  followerUserId: string
): Promise<{ thread_id: string; following: boolean }> {
  const { data } = await client.post<{ thread_id: string; following: boolean }>(
    `/dream-threads/${threadId}/follow`,
    null,
    { params: { follower_user_id: followerUserId } }
  );
  return data;
}

export async function unfollowDreamThread(
  threadId: string,
  followerUserId: string
): Promise<{ thread_id: string; following: boolean }> {
  const { data } = await client.delete<{ thread_id: string; following: boolean }>(
    `/dream-threads/${threadId}/follow`,
    { params: { follower_user_id: followerUserId } }
  );
  return data;
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
  const { data } = await client.post<Encouragement>(
    `/dream-updates/${updateId}/encouragements`,
    { user_id: userId, message }
  );
  return data;
}

export async function getEncouragements(updateId: string): Promise<Encouragement[]> {
  const { data } = await client.get<Encouragement[]>(`/dream-updates/${updateId}/encouragements`);
  return data;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<{ status: string; timestamp: string; backend_configured: boolean }> {
  const { data } = await client.get('/health');
  return data;
}

// ---------------------------------------------------------------------------
// Admin functions
// ---------------------------------------------------------------------------

export async function approveDreamUpdate(updateId: string): Promise<{ update_id: string; status: string }> {
  const { data } = await client.post<{ update_id: string; status: string }>(
    `/admin/moderate/dream-update/${updateId}/approve`
  );
  return data;
}

export async function rejectDreamUpdate(
  updateId: string,
  reason?: string
): Promise<{ update_id: string; status: string; reason?: string }> {
  const { data } = await client.post<{ update_id: string; status: string; reason?: string }>(
    `/admin/moderate/dream-update/${updateId}/reject`,
    null,
    { params: { reason } }
  );
  return data;
}

export default client;
