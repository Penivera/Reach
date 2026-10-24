import { api } from "./api";

export type ProvisioningStatus = "pending" | "provisioned" | "failed";
export type PaymentStatus = "created" | "pending" | "paid" | "failed" | "expired" | "reversed";
export type PayoutStatus = "scheduled" | "created" | "processing" | "completed" | "failed" | "reversed" | "needs_review";

export interface PaymentProfileUpsert {
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  middle_name?: string;
  date_of_birth: string; // YYYY-MM-DD
  address: string;
  city: string;
  country?: string; // defaults to Nigeria
}

export interface PaymentProfileStateResponse {
  profile_completed: boolean;
  can_pay: boolean;
  missing_fields: string[];
  profile: {
    id: number;
    user_id: number;
    middle_name?: string | null;
    date_of_birth: string;
    address: string;
    city: string;
    country: string;
  } | null;
  provisioning: {
    status: ProvisioningStatus;
    provider_customer_id?: string | null;
    wallet_id?: string | null;
    account_number?: string | null;
    account_name?: string | null;
    bank_name?: string | null;
    bank_code?: string | null;
    last_error?: string | null;
  } | null;
}

export interface PaymentIntentResponse {
  id: number;
  job_id: number;
  reference: string;
  amount_kobo: number;
  amount_payable_kobo: number;
  status: PaymentStatus;
  provider_checkout_id: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  expires_at: string;
  paid_at?: string | null;
}

export interface PayoutResponse {
  id: number;
  payment_intent_id: number;
  reference: string;
  amount_kobo: number;
  commission_kobo: number;
  provider_payout_kobo: number;
  status: PayoutStatus;
  provider_payout_id?: string | null;
  failure_reason?: string | null;
  completed_at?: string | null;
}

// --- API Functions ---

export const getPaymentProfile = () =>
  api<PaymentProfileStateResponse>("/payments/profile");

export const updatePaymentProfile = (data: PaymentProfileUpsert) =>
  api<PaymentProfileStateResponse>("/payments/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const retryProvisioning = () =>
  api<PaymentProfileStateResponse>("/payments/profile/provision", {
    method: "POST",
  });

export const createJobCheckout = (jobId: number | string) =>
  api<PaymentIntentResponse>(`/payments/jobs/${jobId}/checkout`, {
    method: "POST",
  });

export const getJobPayment = (jobId: number | string) =>
  api<PaymentIntentResponse>(`/payments/jobs/${jobId}`);

export const releaseJobPayment = (jobId: number | string) =>
  api<PayoutResponse>(`/payments/jobs/${jobId}/release`, {
    method: "POST",
  });

export const getJobPayout = (jobId: number | string) =>
  api<PayoutResponse>(`/payments/jobs/${jobId}/payout`);