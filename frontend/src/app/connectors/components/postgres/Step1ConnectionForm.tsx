'use client';

import React from 'react';
import { Button } from '@/kit';
import { PostgresConnectionConfig } from './types';

interface Step1Props {
  config: PostgresConnectionConfig;
  onChange: (cfg: PostgresConnectionConfig) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
}

export function Step1ConnectionForm({ config, onChange, onSubmit, loading }: Step1Props) {
  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted-foreground">Connector Name</label>
        <input
          className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
          value={config.name}
          onChange={(e) => onChange({ ...config, name: e.target.value })}
          required
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div className="col-span-2">
          <label className="text-xs font-medium text-muted-foreground">Host</label>
          <input
            className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
            value={config.host}
            onChange={(e) => onChange({ ...config, host: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Port</label>
          <input
            type="number"
            className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
            value={config.port}
            onChange={(e) => onChange({ ...config, port: Number(e.target.value) })}
            required
          />
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground">Database</label>
        <input
          className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
          value={config.database}
          onChange={(e) => onChange({ ...config, database: e.target.value })}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs font-medium text-muted-foreground">Username</label>
          <input
            className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
            value={config.username}
            onChange={(e) => onChange({ ...config, username: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Password</label>
          <input
            type="password"
            className="w-full mt-1 px-3 py-1.5 text-xs bg-background border border-border rounded-sm"
            value={config.password}
            onChange={(e) => onChange({ ...config, password: e.target.value })}
            required
          />
        </div>
      </div>
      <div className="flex justify-end pt-3">
        <Button type="submit" disabled={loading} className="text-xs">
          {loading ? 'Testing & Discovering...' : 'Connect & Discover →'}
        </Button>
      </div>
    </form>
  );
}

