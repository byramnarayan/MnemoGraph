'use client';

import React, { useState } from 'react';
import { DiscoveredPerson, ProvisionUserPayload } from '../types';
import { getToken } from '@/lib/api-client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ProvisionUserModalProps {
  person: DiscoveredPerson | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ProvisionUserModal({
  person,
  isOpen,
  onClose,
  onSuccess,
}: ProvisionUserModalProps) {
  if (!isOpen || !person) return null;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('Welcome2026!');
  const [role, setRole] = useState(person.inferred_role || 'Member');
  const [department, setDepartment] = useState(person.inferred_department || 'Engineering');
  const [clearanceLevel, setClearanceLevel] = useState('Internal');
  const [title, setTitle] = useState(person.inferred_role || 'Staff Engineer');
  const [location, setLocation] = useState('US-East');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setErrorMsg(null);

    const payload: ProvisionUserPayload = {
      person_entity_id: person.entity_id,
      full_name: person.full_name,
      email: email.trim().toLowerCase(),
      password,
      role,
      department,
      clearance_level: clearanceLevel,
      title,
      location,
    };

    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/users/provision-discovered-person`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to provision user account.');
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Provisioning error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs font-mono text-xs">
      <div className="w-full max-w-lg bg-card border border-border rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="space-y-0.5">
            <h3 className="font-bold text-sm text-foreground">
              Provision Institutional User Account
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Candidate: <span className="text-foreground font-semibold">{person.full_name}</span> ({person.entity_id})
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded-md hover:bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground"
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-300 text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">
                Work Email <span className="text-[9px] text-accent font-medium">(Welcome email sent here)</span>
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="sarah@corp.internal"
                className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Initial Password</label>
              <input
                type="text"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Assigned Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Clearance Level</label>
              <select
                value={clearanceLevel}
                onChange={(e) => setClearanceLevel(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              >
                <option value="Internal">Internal (Level 1)</option>
                <option value="Confidential">Confidential (Level 2)</option>
                <option value="Restricted">Restricted (Level 3 - Highest)</option>
                <option value="Public">Public (Level 0)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Department</label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Job Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-xs text-muted-foreground"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !email}
              className="px-4 py-1.5 rounded-lg bg-accent text-accent-foreground font-semibold text-xs hover:opacity-90 disabled:opacity-50"
            >
              {isLoading ? 'Creating & Dispatching...' : 'Provision Account & Send Login Email'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

