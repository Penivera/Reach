import { api } from "./api";

export function signup(data: {
  first_name: string;
  last_name: string;
  email: string;
  username: string;
  phone_number: string;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  hashed_password: string;
  confirm_password: string;
}) {
  return api("/auth/create-user", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function verifyEmail(token: string) {
  return api("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function resendVerification(email: string) {
  return api(
    `/auth/resend-verification?email=${encodeURIComponent(email)}`,
    {
      method: "POST",
    }
  );
}

export function login(
  username: string,
  password: string
) {
  const body = new FormData();

  body.append("username", username);
  body.append("password", password);

  return api("/auth/login", {
    method: "POST",
    body,
  });
}

export function forgotPassword(email: string) {
  return api(
    `/auth/forgot-password?email=${encodeURIComponent(email)}`,
    {
      method: "POST",
    }
  );
}

export function resetPassword(
  token: string,
  newPassword: string
) {
  return api(
    `/auth/reset-password?token=${encodeURIComponent(token)}&new_password=${encodeURIComponent(newPassword)}`,
    {
      method: "POST",
    }
  );
}

export function changePassword(data: {
  current_password: string;
  new_password: string;
}) {
  return api("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function logout() {
  return api("/auth/logout", {
    method: "POST",
  });
}
