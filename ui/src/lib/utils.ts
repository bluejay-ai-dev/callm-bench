import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const pct = (n: number, d: number) => (d ? `${Math.round((100 * n) / d)}%` : "–");

export function ago(iso?: string | null) {
  if (!iso) return "–";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.round(s)}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function duration(start?: string | null, end?: string | null) {
  if (!start) return "–";
  const s = Math.round(((end ? new Date(end) : new Date()).getTime() - new Date(start).getTime()) / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

export const go = (hash: string) => {
  location.hash = hash;
};
