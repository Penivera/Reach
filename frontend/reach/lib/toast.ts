export type ToastVariant = "success" | "error" | "info";

export interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

type Listener = (toasts: ToastItem[]) => void;

let toasts: ToastItem[] = [];
let listeners: Listener[] = [];
let counter = 0;

function emit() {
  listeners.forEach((l) => l(toasts));
}

function push(message: string, variant: ToastVariant, duration = 4000) {
  const id = ++counter;
  toasts = [...toasts, { id, message, variant }];
  emit();
  setTimeout(() => dismiss(id), duration);
}

function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export const toast = {
  success: (message: string) => push(message, "success"),
  error: (message: string) => push(message, "error"),
  info: (message: string) => push(message, "info"),
};

export function subscribeToasts(listener: Listener): () => void {
  listeners.push(listener);
  listener(toasts);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

export function dismissToast(id: number) {
  dismiss(id);
}