#!/usr/bin/env python3
"""
Ingest documents into the knowledge base for a tenant.

Supports PDF, plain text (.txt), and Markdown (.md) files.
Documents are split into ~500-char chunks, embedded with OpenAI
text-embedding-3-small, and stored in Supabase kb_chunks.

Usage:
  # Single PDF
  python scripts/ingest_kb.py --tenant TENANT_UUID --file docs/pricing.pdf

  # Single text/markdown file
  python scripts/ingest_kb.py --tenant TENANT_UUID --file docs/faqs.txt

  # Whole directory (processes .pdf, .txt, .md)
  python scripts/ingest_kb.py --tenant TENANT_UUID --dir docs/

  # Inline text string
  python scripts/ingest_kb.py --tenant TENANT_UUID \
      --text "Emergency call-out fee: $150 flat rate, applies 24/7."
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.rag import ingest_chunk
from src.utils.text import split_text

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md")


def extract_text(path: str) -> str:
    """Extract plain text from a file. Handles PDF, .txt, and .md."""
    if path.lower().endswith(".pdf"):
        return _extract_pdf(path)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: pypdf is not installed. Run: pip install pypdf")
        sys.exit(1)

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


async def ingest_file(tenant_id: str, path: str) -> None:
    text = extract_text(path)
    if not text.strip():
        print(f"  WARNING: no text extracted from {path} — skipping")
        return

    chunks = split_text(text)
    source = os.path.basename(path)
    print(f"  {source}: {len(chunks)} chunks")

    for i, chunk in enumerate(chunks, 1):
        chunk_id = await ingest_chunk(tenant_id, chunk, {"source": source})
        print(f"    [{i}/{len(chunks)}] {chunk_id[:12]}...  ({len(chunk)} chars)")


async def main(args: argparse.Namespace) -> None:
    tenant_id = args.tenant

    if args.text:
        chunks = split_text(args.text)
        print(f"Ingesting {len(chunks)} chunks from --text...")
        for i, chunk in enumerate(chunks, 1):
            chunk_id = await ingest_chunk(tenant_id, chunk, {"source": "cli"})
            print(f"  [{i}/{len(chunks)}] {chunk_id[:12]}...  ({len(chunk)} chars)")

    elif args.file:
        print(f"Ingesting {args.file}...")
        await ingest_file(tenant_id, args.file)

    elif args.dir:
        files = [
            f for f in os.listdir(args.dir)
            if f.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if not files:
            print(f"No .pdf / .txt / .md files found in {args.dir}")
            return
        print(f"Ingesting {len(files)} files from {args.dir}...")
        for fname in sorted(files):
            await ingest_file(tenant_id, os.path.join(args.dir, fname))

    else:
        print("Provide one of: --file, --dir, or --text")
        sys.exit(1)

    print("\nDone.")


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest KB docs for a Turboman tenant")
    parser.add_argument("--tenant", required=True, help="Tenant UUID from Supabase")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="Path to a PDF, .txt, or .md file")
    group.add_argument("--dir", help="Directory containing PDF / .txt / .md files")
    group.add_argument("--text", help="Inline text string to ingest")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(_parse()))
