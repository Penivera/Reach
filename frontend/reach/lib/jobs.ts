import { api } from "./api";

export type JobStatus = "open" | "in_progress" | "completed" | "cancelled";
export type ApplicationStatus = "pending" | "accepted" | "rejected" | "withdrawn";

export type Job = {
  id: number;
  title: string;
  description: string;
  budget: number;
  status: JobStatus;
  category_id: number;
  posted_by: number;
  latitude: number;
  longitude: number;
  location_name: string;
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
};

export type UpdateJobInput = {
  title: string;
  description: string;
  budget: number;
  latitude: number;
  longitude: number;
  location_name: string;
};

export type JobApplication = {
  id: number;
  job_id: number;
  applicant_id: number;
  proposal_text: string;
  proposed_price: number;
  status: ApplicationStatus;
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

export function createJob(data: CreateJobInput) {
  return api("/jobs", {
    method: "POST",
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

export function updateJob(jobId: number, data: UpdateJobInput) {
  return api(`/jobs/${jobId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

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

export function getJobApplications(jobId: number) : Promise<JobApplication[]> {
  return api(`/jobs/${jobId}/applications`, {
    method: "GET",
  });
}

export function getMyJobApplications() {
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
  });
}