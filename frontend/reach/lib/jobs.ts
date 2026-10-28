import { api } from "./api";

export type JobStatus = "open" | "in_progress" | "completed" | "cancelled";
export type ApplicationStatus = "pending" | "accepted" | "rejected" | "withdrawn";
export type UrgencyLevel = "asap" | "this_week" | "flexible";

export type Job = {
  id: number;
  title: string;
  description: string;
  budget: number;
  status: JobStatus;
  urgency: UrgencyLevel;
  expires_at: string | null;
  category_id: number;
  posted_by: number;
  latitude: number;
  longitude: number;
  location_name: string;
  onchain_task_id?: number;
  onchain_tx_hash?: string;
  /** @deprecated Deprecated in favor of onchain_task_id (Model 1: Solana is canonical) */
  near_task_id?: number;
  created_at: string;
  updated_at: string;
};

export type CreateJobInput = {
  latitude: number;
  longitude: number;
  location_name: string;
  category_id: number;
  title: string;
  description: string;
  budget: number;
  urgency: UrgencyLevel;
};

export type UpdateJobInput = {
  title: string;
  description: string;
  budget: number;
  latitude: number;
  longitude: number;
  location_name: string;
  urgency?: UrgencyLevel;
};

export type JobApplication = {
  id: number;
  job_id: number;
  applicant_id: number;
  proposal_text: string;
  proposed_price: number;
  status: ApplicationStatus;
  onchain_application_id?: number;
  /** @deprecated Deprecated in favor of onchain_application_id (Model 1: Solana is canonical) */
  near_application_id?: number;
  created_at: string;
  updated_at: string;
};

export type CreateJobApplicationInput = {
  proposal_text: string;
  proposed_price: number;
};

export type UpdateJobApplicationInput = {
  proposal_text: string;
  proposed_price: number;
};

export type UpdateApplicationStatusInput = {
  status: ApplicationStatus;
};

export function getJobs(): Promise<Job[]> {
  return api("/jobs", {
    method: "GET",
  });
}

// export function createJob(data: CreateJobInput) {
//   return api("/jobs", {
//     method: "POST",
//     body: JSON.stringify(data),
//   });
// }

export function createJob(data: CreateJobInput): Promise<Job> {
  return api<Job>("/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateJob(jobId: number, data: UpdateJobInput): Promise<Job> {
  return api<Job>(`/jobs/${jobId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function getMyJobs() {
  return api("/jobs/me", {
    method: "GET",
  });
}

export function getJob(jobId: number): Promise<Job> {
  return api(`/jobs/${jobId}`, {
    method: "GET",
  });
}

// export function updateJob(jobId: number, data: UpdateJobInput) {
//   return api(`/jobs/${jobId}`, {
//     method: "PUT",
//     body: JSON.stringify(data),
//   });
// }

export function deleteJob(jobId: number) {
  return api(`/jobs/${jobId}`, {
    method: "DELETE",
  });
}

export function applyToJob(jobId: number, data: CreateJobApplicationInput): Promise<JobApplication> {
  return api(`/jobs/${jobId}/apply`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getJobApplications(jobId: number): Promise<JobApplication[]> {
  return api(`/jobs/${jobId}/applications`, {
    method: "GET",
    silentStatuses: [403],
  });
}

export function getMyJobApplications(): Promise<JobApplication[]> {
  return api("/jobs/applications/me", {
    method: "GET",
  });
}

export function updateApplication(id: number, data: UpdateJobApplicationInput) {
  return api(`/jobs/applications/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteApplication(id: number) {
  return api(`/jobs/applications/${id}`, {
    method: "DELETE",
  });
}

export function updateApplicationStatus(
  id: number,
  data: UpdateApplicationStatusInput
): Promise<JobApplication> {
  return api(`/jobs/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function getAcceptedApplication(jobId: number): Promise<JobApplication> {
  return api(`/jobs/${jobId}/accepted-application`, {
    method: "GET",
    silentStatuses: [403, 404],
  });
}

/**
 * Link on-chain task ID to job.
 * @param onchain_task_id - Canonical Solana Anchor task ID (or legacy NEAR task ID)
 */
export function linkJobChain(jobId: number, onchain_task_id: number, onchain_tx_hash?: string) {
  const params = new URLSearchParams({
    onchain_task_id: onchain_task_id.toString(),
    near_task_id: onchain_task_id.toString(), // backward compatibility
  });
  if (onchain_tx_hash) {
    params.append("onchain_tx_hash", onchain_tx_hash);
  }
  return api(`/jobs/${jobId}/link-chain?${params.toString()}`, { method: "PATCH" });
}

export function linkApplicationChain(id: number, onchain_application_id: number) {
  const params = new URLSearchParams({
    onchain_application_id: onchain_application_id.toString(),
    near_application_id: onchain_application_id.toString(), // backward compatibility
  });
  return api(`/jobs/applications/${id}/link-chain?${params.toString()}`, { method: "PATCH" });
}
export function completeJob(jobId: number): Promise<Job> {
  return api(`/jobs/${jobId}/completion`, { method: "PATCH" });
}
