'use client';

import React from 'react';
import { Button } from '@/kit';
import { DocumentUploadResult } from './types';

interface DocumentUploadStatusRowProps {
  uploading: boolean;
  stepText: string | null;
  error: string | null;
  result: DocumentUploadResult | null;
  hasFile: boolean;
}

export function DocumentUploadStatusRow({
  uploading,
  stepText,
  error,
  result,
  hasFile,
}: DocumentUploadStatusRowProps) {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
      <div className="text-xs">
        {uploading && (
          <div className="flex items-center gap-2 text-sky-400 font-mono text-[11px] animate-pulse">
            <span className="w-2 h-2 rounded-full bg-sky-400 inline-block animate-ping" />
            {stepText || 'Ingesting document through pipeline...'}
          </div>
        )}
        {error && <span className="text-red-400 text-xs font-mono">Error: {error}</span>}
        {result && (
          <div className="text-emerald-400 text-xs font-mono flex items-center gap-2">
            <svg
              className="w-4 h-4 text-emerald-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            Ingested: &quot;{result.title}&quot; • {result.indexed_chunks} vector chunks indexed •{' '}
            {result.entities_found} entities linked
          </div>
        )}
      </div>

      <Button
        type="submit"
        disabled={uploading || !hasFile}
        className="w-full sm:w-auto bg-sky-600 hover:bg-sky-500 text-white font-semibold px-4 py-2 text-xs shadow-[0_0_15px_rgba(14,165,233,0.3)] transition-all"
      >
        {uploading ? 'Processing Pipeline...' : 'Upload & Run Pipeline'}
      </Button>
    </div>
  );
}

