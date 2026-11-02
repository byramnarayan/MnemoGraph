'use client';

import React, { useState, useRef } from 'react';
import { api } from '@/lib/api-client';
import { Button, Panel, Tag } from '@/kit';

interface DocumentUploadSectionProps {
  onSuccess?: () => void;
}

export function DocumentUploadSection({ onSuccess }: DocumentUploadSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [classification, setClassification] = useState('Internal');
  const [uploading, setUploading] = useState(false);
  const [stepText, setStepText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ''));
      }
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to ingest.');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);
    setStepText('1/4 Storing raw binary into MinIO / S3...');

    const timer1 = setTimeout(() => {
      setStepText('2/4 Parsing text & extracting structural entities...');
    }, 600);

    const timer2 = setTimeout(() => {
      setStepText('3/4 Ingesting into FalkorDB Canonical Graph...');
    }, 1200);

    const timer3 = setTimeout(() => {
      setStepText('4/4 Computing dense vectors & indexing into Qdrant...');
    }, 1800);

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (title.trim()) {
        formData.append('title', title.trim());
      }
      formData.append('classification', classification);

      const res = await api.connectors.uploadDocument(formData);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setResult(res);
      setStepText(null);
      setFile(null);
      setTitle('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setError(err.message || 'Document ingestion failed.');
      setStepText(null);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Panel className="p-5 border border-sky-500/20 bg-card/60 relative overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-sm bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Upload & Ingest Knowledge Document</h3>
            <p className="text-xs text-muted-foreground">
              Direct pipeline ingest into Object Storage, PostgreSQL, FalkorDB Graph & Qdrant Vectors.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Tag tone="accent">Pipeline Ingestion</Tag>
          <span className="text-[10px] font-mono text-muted-foreground">PDF • DOCX • MD • TXT • JSON • CSV</span>
        </div>
      </div>

      <form onSubmit={handleUpload} className="mt-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* File Picker */}
          <div className="space-y-1 md:col-span-1">
            <label className="text-[11px] font-mono text-muted-foreground uppercase">File</label>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              disabled={uploading}
              accept=".pdf,.docx,.doc,.txt,.md,.markdown,.json,.csv"
              className="w-full text-xs text-muted-foreground file:mr-2 file:py-1.5 file:px-3 file:rounded-xs file:border-0 file:text-xs file:font-mono file:bg-sky-500/10 file:text-sky-300 hover:file:bg-sky-500/20 cursor-pointer bg-background/50 p-1.5 rounded-sm border border-border"
            />
          </div>

          {/* Document Title */}
          <div className="space-y-1 md:col-span-1">
            <label className="text-[11px] font-mono text-muted-foreground uppercase">Document Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={uploading}
              placeholder="e.g. 5G RAN Fronthaul Specs"
              className="w-full bg-background/50 border border-border rounded-sm px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Security Classification */}
          <div className="space-y-1 md:col-span-1">
            <label className="text-[11px] font-mono text-muted-foreground uppercase">Security Scope</label>
            <select
              value={classification}
              onChange={(e) => setClassification(e.target.value)}
              disabled={uploading}
              className="w-full bg-background/50 border border-border rounded-sm px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="Internal">Internal (Company-Wide)</option>
              <option value="Confidential">Confidential (Assigned Team)</option>
              <option value="Restricted">Restricted (Executive Only)</option>
            </select>
          </div>
        </div>

        {/* Action Row */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <div className="text-xs">
            {uploading && (
              <div className="flex items-center gap-2 text-sky-400 font-mono text-[11px] animate-pulse">
                <span className="w-2 h-2 rounded-full bg-sky-400 inline-block animate-ping" />
                {stepText || 'Ingesting document through pipeline...'}
              </div>
            )}
            {error && (
              <span className="text-red-400 text-xs font-mono">
                Error: {error}
              </span>
            )}
            {result && (
              <div className="text-emerald-400 text-xs font-mono flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                Ingested: &quot;{result.title}&quot; • {result.indexed_chunks} vector chunks indexed • {result.entities_found} entities linked
              </div>
            )}
          </div>

          <Button
            type="submit"
            disabled={uploading || !file}
            className="w-full sm:w-auto bg-sky-600 hover:bg-sky-500 text-white font-semibold px-4 py-2 text-xs shadow-[0_0_15px_rgba(14,165,233,0.3)] transition-all"
          >
            {uploading ? 'Processing Pipeline...' : 'Upload & Run Pipeline'}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

