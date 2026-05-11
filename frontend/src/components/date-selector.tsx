"use client";
import { useState, useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { todayStr, toLocalDateStr } from "@/lib/date-groups";

const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function yesterdayStr() {
  return toLocalDateStr(new Date(Date.now() - 864e5).toISOString());
}

function displayLabel(dateStr: string): string {
  const today = todayStr();
  const yesterday = yesterdayStr();
  if (dateStr === today) return "Today";
  if (dateStr === yesterday) return "Yesterday";
  return new Date(dateStr + "T12:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export function DateSelector({
  value,
  onChange,
  count,
  noun = "result",
}: {
  value: string;
  onChange: (d: string) => void;
  count?: number;
  noun?: string;
}) {
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => new Date(value + "T12:00:00").getFullYear());
  const [viewMonth, setViewMonth] = useState(() => new Date(value + "T12:00:00").getMonth());
  const ref = useRef<HTMLDivElement>(null);
  const today = todayStr();
  const yesterday = yesterdayStr();

  // Sync calendar view when value changes from outside
  useEffect(() => {
    const d = new Date(value + "T12:00:00");
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
  }, [value]);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const todayDate = new Date(today + "T12:00:00");
  const atCurrentMonth = viewYear === todayDate.getFullYear() && viewMonth === todayDate.getMonth();

  function prevMonth() {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  }

  function nextMonth() {
    if (atCurrentMonth) return;
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  }

  function selectDay(day: number) {
    const d = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    if (d > today) return;
    onChange(d);
    setOpen(false);
  }

  function quickSelect(dateStr: string) {
    onChange(dateStr);
    setOpen(false);
  }

  // Build calendar grid
  const firstDayOfWeek = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDayOfWeek).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const isCustomDate = value !== today && value !== yesterday;

  return (
    <div className="flex flex-wrap items-center gap-2" ref={ref}>
      {/* Quick picks */}
      <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
        {([{ label: "Yesterday", d: yesterday }, { label: "Today", d: today }] as const).map(({ label, d }) => (
          <button
            key={label}
            onClick={() => quickSelect(d)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
              value === d
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Calendar trigger */}
      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all duration-150 ${
            isCustomDate || open
              ? "border-brand bg-brand text-white shadow-sm shadow-brand/25"
              : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          <CalendarDays size={13} />
          {isCustomDate ? displayLabel(value) : "Pick date"}
        </button>

        {open && (
          <div className="absolute right-0 top-full mt-2 z-50 bg-white rounded-2xl shadow-2xl border border-slate-100 p-4 w-[280px] select-none">

            {/* Month navigation */}
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={prevMonth}
                className="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <ChevronLeft size={15} />
              </button>
              <span className="text-sm font-semibold text-slate-800">
                {MONTHS[viewMonth]} {viewYear}
              </span>
              <button
                onClick={nextMonth}
                disabled={atCurrentMonth}
                className="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-30 disabled:cursor-default disabled:hover:bg-transparent"
              >
                <ChevronRight size={15} />
              </button>
            </div>

            {/* Day-of-week headers */}
            <div className="grid grid-cols-7 mb-2">
              {DAYS.map((d) => (
                <div key={d} className="text-center text-[10px] font-semibold text-slate-400 tracking-wide py-1">
                  {d}
                </div>
              ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7 gap-y-1">
              {cells.map((day, i) => {
                if (!day) return <div key={i} />;
                const dateStr = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                const isSelected = dateStr === value;
                const isToday = dateStr === today;
                const isFuture = dateStr > today;

                return (
                  <button
                    key={i}
                    onClick={() => !isFuture && selectDay(day)}
                    disabled={isFuture}
                    className={`relative mx-auto w-9 h-9 flex items-center justify-center rounded-xl text-xs font-medium transition-all duration-100 ${
                      isSelected
                        ? "bg-brand text-white shadow-md shadow-brand/30 scale-105"
                        : isFuture
                        ? "text-slate-200 cursor-default"
                        : isToday
                        ? "text-brand font-bold hover:bg-brand/10"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {day}
                    {isToday && !isSelected && (
                      <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-brand" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Footer */}
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={() => quickSelect(today)}
                className="text-xs font-medium text-brand hover:text-brand-dark transition-colors"
              >
                Jump to today
              </button>
              <span className="text-xs text-slate-400">{displayLabel(value)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Count label */}
      {count !== undefined && (
        <span className="text-xs text-slate-400">
          {count} {noun}{count !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}
