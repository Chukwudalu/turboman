"use client";
import { useCallback, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import useSWR from "swr";
import { Upload, Trash2, FileText, Loader2, BookOpen } from "lucide-react";
import clsx from "clsx";
import { api, KBChunk } from "@/lib/api";

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "";

function fmt(ts: string) {
  return new Date(ts).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function truncate(s: string, n = 140) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

export default function KnowledgeBasePage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";

  const { data: chunks, isLoading, mutate } = useSWR(
    token ? ["kb", token] : null,
    ([, t]) => api.kbChunks(t, TENANT_ID)
  );

  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0 || !token) return;
    const file = files[0];

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "txt", "md"].includes(ext ?? "")) {
      setUploadError("Only PDF, .txt, and .md files are supported.");
      return;
    }

    setUploading(true);
    setUploadResult(null);
    setUploadError(null);

    try {
      const res = await api.uploadKbFile(token, TENANT_ID, file);
      setUploadResult(`"${res.filename}" added — ${res.chunks_added} chunks ingested.`);
      mutate();
    } catch (e: any) {
      setUploadError(e.message ?? "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }, [token, mutate]);

  const handleDelete = async (chunk: KBChunk) => {
    if (!confirm(`Delete this chunk from "${chunk.metadata?.source ?? "unknown"}"?`)) return;
    setDeletingId(chunk.id);
    try {
      await api.deleteKbChunk(token, chunk.id);
      mutate();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-5xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Knowledge Base</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload documents so the AI agent can answer questions about your business.
          Supports PDF, .txt, and .md files.
        </p>
      </div>

      {/* Upload area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        className={clsx(
          "border-2 border-dashed rounded-xl p-8 sm:p-12 flex flex-col items-center gap-3 transition-all cursor-pointer",
          dragOver
            ? "border-brand bg-brand/5 scale-[1.01]"
            : "border-slate-200 bg-white hover:border-brand/50 hover:bg-slate-50/50"
        )}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <>
            <div className="w-12 h-12 rounded-2xl bg-brand/10 flex items-center justify-center">
              <Loader2 size={22} className="text-brand animate-spin" />
            </div>
            <p className="text-sm font-medium text-slate-600">Uploading and embedding…</p>
            <p className="text-xs text-slate-400">This may take a moment</p>
          </>
        ) : (
          <>
            <div className={clsx(
              "w-12 h-12 rounded-2xl flex items-center justify-center transition-colors",
              dragOver ? "bg-brand/10" : "bg-slate-100"
            )}>
              <Upload size={20} className={clsx(dragOver ? "text-brand" : "text-slate-400")} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-700">
                Drop a file here, or{" "}
                <span className="text-brand">click to browse</span>
              </p>
              <p className="text-xs text-slate-400 mt-1">PDF, .txt, .md — max 10 MB</p>
            </div>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {uploadResult && (
        <div className="flex items-start gap-3 rounded-xl bg-green-50 border border-green-200 px-4 py-3.5 text-sm text-green-800">
          <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
          {uploadResult}
        </div>
      )}
      {uploadError && (
        <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 px-4 py-3.5 text-sm text-red-800">
          <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
          {uploadError}
        </div>
      )}

      {/* Chunks list */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen size={15} className="text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-700">Stored chunks</h2>
          </div>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {chunks?.data.length ?? 0} total
          </span>
        </div>

        {isLoading && (
          <div className="px-5 py-12 text-center text-slate-400 text-sm">Loading…</div>
        )}
        {!isLoading && !chunks?.data.length && (
          <div className="px-5 py-12 flex flex-col items-center gap-2 text-slate-400 text-sm">
            <FileText size={28} className="text-slate-200" />
            <p>No documents ingested yet. Upload your first file above.</p>
          </div>
        )}

        <ul className="divide-y divide-slate-100">
          {chunks?.data.map((chunk) => (
            <li key={chunk.id} className="px-5 py-4 flex items-start gap-4 hover:bg-slate-50/50 transition-colors">
              <div className="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                <FileText size={13} className="text-slate-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-400 mb-1">
                  {chunk.metadata?.source ?? "unknown"}
                  <span className="mx-1.5 text-slate-300">·</span>
                  {fmt(chunk.created_at)}
                </p>
                <p className="text-sm text-slate-700 leading-relaxed">{truncate(chunk.content)}</p>
              </div>
              <button
                onClick={() => handleDelete(chunk)}
                disabled={deletingId === chunk.id}
                className="shrink-0 w-7 h-7 rounded-md flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
                title="Delete chunk"
              >
                {deletingId === chunk.id
                  ? <Loader2 size={14} className="animate-spin" />
                  : <Trash2 size={14} />
                }
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
