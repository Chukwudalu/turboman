export function toLocalDateStr(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

export function todayStr(): string {
  return toLocalDateStr(new Date().toISOString());
}

export function filterByDate<T>(
  items: T[],
  getIso: (item: T) => string,
  dateStr: string,
): T[] {
  return items.filter((item) => toLocalDateStr(getIso(item)) === dateStr);
}
