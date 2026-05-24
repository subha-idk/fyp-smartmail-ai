/**
 * SmartMail AI+ — Typed API client.
 *
 * Centralizes all backend communication with API key auth.
 * From CONTEXT.md Section 7.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "X-API-Key": KEY,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export interface SummaryStats {
  total_users: number;
  total_products: number;
  total_events: number;
  total_campaigns: number;
  emails_sent: number;
  emails_opened: number;
  emails_clicked: number;
  emails_failed: number;
  emails_bounced: number;
  total_emails: number;
  avg_engagement_score: number;
  conversion_rate: number;
  open_rate: number;
  click_rate: number;
}

export interface EventSeriesPoint {
  date: string;
  count: number;
}

export interface UserProfileData {
  user_id: string;
  total_events: number;
  total_purchases: number;
  total_spend: number;
  last_active_at: string | null;
  days_since_last_purchase: number | null;
  preferred_categories: string[];
  top_viewed_products: string[];
  engagement_score: number;
  churn_risk: number | null;
  purchase_probability: number | null;
  rfm_recency: number | null;
  rfm_frequency: number | null;
  rfm_monetary: number | null;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  country: string | null;
  created_at: string;
  profile: {
    total_events: number;
    total_purchases: number;
    total_spend: number;
    last_active_at: string | null;
    engagement_score: number | null;
  } | null;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  is_active: boolean;
  created_at: string;
}

export interface EmailLog {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  email_type: string;
  subject: string | null;
  status: string;
  sent_at: string;
  opened_at: string | null;
  clicked_at: string | null;
  tokens_used: number;
}

export interface SendEmailResponse {
  log_id?: string;
  status: string;
  email_type?: string;
  subject?: string;
  reason?: string;
  tokens_used?: number;
}

export function fetchSummary(): Promise<SummaryStats> {
  return apiFetch<SummaryStats>("/api/analytics/summary");
}

export function fetchEventSeries(days: number = 30, eventType?: string): Promise<EventSeriesPoint[]> {
  let path = `/api/analytics/events?days=${days}`;
  if (eventType) {
    path += `&event_type=${eventType}`;
  }
  return apiFetch<EventSeriesPoint[]>(path);
}

export function fetchUsers(
  page: number,
  limit: number,
  q?: string,
): Promise<{ users: User[]; total: number; page: number; limit: number }> {
  const query = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });
  if (q) {
    query.set("q", q);
  }
  return apiFetch<{ users: User[]; total: number; page: number; limit: number }>(
    `/api/users?${query.toString()}`,
  );
}

export function fetchUserProfile(id: string): Promise<UserProfileData> {
  return apiFetch<UserProfileData>(`/api/users/${id}/profile`);
}

export function fetchRecommendations(id: string, n: number = 3): Promise<Product[]> {
  return apiFetch<Product[]>(`/api/recommend/${id}?n=${n}`);
}

export function triggerSendEmail(id: string): Promise<SendEmailResponse> {
  return apiFetch<SendEmailResponse>(`/api/send-email/${id}`, {
    method: "POST",
  });
}

export function fetchEmailLogs(
  page: number = 1,
  limit: number = 20,
): Promise<{ logs: EmailLog[]; total: number }> {
  return apiFetch<{ logs: EmailLog[]; total: number }>(
    `/api/email_logs?page=${page}&limit=${limit}`,
  );
}
