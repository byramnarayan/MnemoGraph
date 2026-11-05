'use client';

import React from 'react';

interface DocumentUploadFieldsProps {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  title: string;
  onTitleChange: (val: string) => void;
  classification: string;
  onClassificationChange: (val: string) => void;
  disabled: boolean;
}

export function DocumentUploadFields({
  fileInputRef,
  onFileChange,
  title,
  onTitleChange,
  classification,
  onClassificationChange,
  disabled,
}: DocumentUploadFieldsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="space-y-1 md:col-span-1">
        <label className="text-[11px] font-mono text-muted-foreground uppercase">File</label>
        <input
          ref={fileInputRef}
          type="file"
          onChange={onFileChange}
          disabled={disabled}
          accept=".pdf,.docx,.doc,.txt,.md,.markdown,.json,.csv"
          className="w-full text-xs text-muted-foreground file:mr-2 file:py-1.5 file:px-3 file:rounded-xs file:border-0 file:text-xs file:font-mono file:bg-sky-500/10 file:text-sky-300 hover:file:bg-sky-500/20 cursor-pointer bg-background/50 p-1.5 rounded-sm border border-border"
        />
      </div>

      <div className="space-y-1 md:col-span-1">
        <label className="text-[11px] font-mono text-muted-foreground uppercase">
          Document Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          disabled={disabled}
          placeholder="e.g. 5G RAN Fronthaul Specs"
          className="w-full bg-background/50 border border-border rounded-sm px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-sky-500"
        />
      </div>

      <div className="space-y-1 md:col-span-1">
        <label className="text-[11px] font-mono text-muted-foreground uppercase">
          Security Scope
        </label>
        <select
          value={classification}
          onChange={(e) => onClassificationChange(e.target.value)}
          disabled={disabled}
          className="w-full bg-background/50 border border-border rounded-sm px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-sky-500 cursor-pointer"
        >
          <option value="Internal">Internal (Company-Wide)</option>
          <option value="Confidential">Confidential (Assigned Team)</option>
          <option value="Restricted">Restricted (Executive Only)</option>
        </select>
      </div>
    </div>
  );
}

