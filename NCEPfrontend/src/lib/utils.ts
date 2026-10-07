import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = new Date(date);
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}

export function formatDateTime(date: string | Date): string {
  const d = new Date(date);
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  return `${formatDate(d)} ${hours}:${minutes}`;
}

export function formatAuditLogTime(date: string | Date): string {
  const d = new Date(date);
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const seconds = d.getSeconds().toString().padStart(2, '0');
  return `${formatDate(d)} ${hours}:${minutes}:${seconds}`;
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/**
 * Builds a CSV file from an array of objects and triggers a browser download.
 * `columns` controls both which fields are included and their header/order;
 * omit it to use every key of the first row.
 */
export function exportToCsv<T extends Record<string, unknown>>(
  filename: string,
  rows: T[],
  columns?: Array<{ key: keyof T; header: string }>,
): void {
  const cols = columns ?? (rows[0] ? Object.keys(rows[0]).map((key) => ({ key: key as keyof T, header: key })) : []);
  const header = cols.map((c) => csvCell(c.header)).join(",");
  const lines = rows.map((row) => cols.map((c) => csvCell(row[c.key])).join(","));
  const csv = [header, ...lines].join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/** Generates a random temporary password for a newly-created account (share it with the user out-of-band). */
export function generateTempPassword(): string {
  const upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const lower = "abcdefghijkmnpqrstuvwxyz";
  const digits = "23456789";
  const symbols = "!@#$%*?";
  const all = upper + lower + digits + symbols;

  const randomChar = (pool: string) => pool[Math.floor(Math.random() * pool.length)];
  const required = [randomChar(upper), randomChar(lower), randomChar(digits), randomChar(symbols)];
  const rest = Array.from({ length: 8 }, () => randomChar(all));

  return [...required, ...rest].sort(() => Math.random() - 0.5).join("");
}
