'use client';

import React, { useState, useRef } from 'react';
import { api } from '@/lib/api-client';
import { Panel, Tag } from '@/kit';
import { DocumentUploadFields } from './DocumentUploadFields';
import { DocumentUploadStatusRow } from './DocumentUploadStatusRow';
import { DocumentUploadResult } from './types';

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
  const [result, setResult] = useState<DocumentUploadResult | null>(null);
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

    const t1 = setTimeout(() => setStepText('2/4 Parsing text & extracting structural entities...'), 600);
    const t2 = setTimeout(() => setStepText('3/4 Ingesting into FalkorDB Canonical Graph...'), 1200);
    const t3 = setTimeout(() => setStepText('4/4 Computing dense vectors & indexing into Qdrant...'), 1800);

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (title.trim()) {
        formData.append('title', title.trim());
      }
      formData.append('classification', classification);

      const res = await api.connectors.uploadDocument(formData);
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      setResult(res);
      setStepText(null);
      setFile(null);
      setTitle('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onSuccess?.();
    } catch (err: any) {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
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
        <DocumentUploadFields
          fileInputRef={fileInputRef}
          onFileChange={handleFileChange}
          title={title}
          onTitleChange={setTitle}
          classification={classification}
          onClassificationChange={setClassification}
          disabled={uploading}
        />
        <DocumentUploadStatusRow
          uploading={uploading}
          stepText={stepText}
          error={error}
          result={result}
          hasFile={!!file}
        />
      </form>
    </Panel>
  );
}

