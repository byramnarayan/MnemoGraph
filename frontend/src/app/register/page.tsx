'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { Button, Eyebrow, Field, Tag, Callout } from '@/kit';

const DEFAULT_DEPARTMENTS = [
  'Network Operations',
  'Customer Support',
  'Radio Frequency Engineering',
  'Billing & Mediation',
  'Executive Leadership',
];

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  // Step 1: Org Profile
  const [companyName, setCompanyName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [industryVertical, setIndustryVertical] = useState('Telecom & Network Infrastructure');

  // Step 2: Head of Company
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Step 3: Departments
  const [departments, setDepartments] = useState<string[]>(DEFAULT_DEPARTMENTS);
  const [customDept, setCustomDept] = useState('');

  // State
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const addDepartment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customDept.trim()) return;
    if (!departments.includes(customDept.trim())) {
      setDepartments([...departments, customDept.trim()]);
    }
    setCustomDept('');
  };

  const removeDepartment = (dept: string) => {
    setDepartments(departments.filter((d) => d !== dept));
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await register({
        full_name: fullName,
        email: email,
        password: password,
        company_name: companyName,
        tenant_slug: tenantSlug,
        industry_vertical: industryVertical,
        department: departments.join(', '),
        role: 'Executive Admin',
      });
      router.push('/profile');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-12 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
      {/* Container Box */}
      <div className="border border-border/80 bg-card/60 backdrop-blur-sm rounded-lg p-6 sm:p-10 shadow-2xl relative overflow-hidden">
        {/* Glow ambient background effect */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Header Tag & Title */}
        <div className="space-y-3 mb-8">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-accent/10 border border-accent/30 text-accent font-mono text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            Enterprise Multi-Tenant Setup
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
            Provision New Organization & Company Brain
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Register your enterprise tenant, bootstrap departmental silos, and configure master RBAC credentials for complete institutional memory isolation.
          </p>
        </div>

        {error && (
          <div className="mb-6">
            <Callout tone="bad" title="Setup Error">
              {error}
            </Callout>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-8">
          {/* Section 01: Organization Profile */}
          <div className="space-y-4 pt-4 border-t border-border/60">
            <Eyebrow>01 / ORGANIZATION PROFILE</Eyebrow>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field
                label="COMPANY NAME *"
                placeholder="e.g. Apex Telecommunications Ltd."
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                required
              />
              <div>
                <Field
                  label="TENANT IDENTIFIER (SLUG) *"
                  placeholder="e.g. apex_telecom"
                  value={tenantSlug}
                  onChange={(e) => setTenantSlug(e.target.value)}
                  hint="Unique slug used for strict multi-tenant database & graph isolation."
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1.5 font-medium">
                  INDUSTRY VERTICAL
                </label>
                <select
                  value={industryVertical}
                  onChange={(e) => setIndustryVertical(e.target.value)}
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                >
                  <option value="Telecom & Network Infrastructure">Telecom & Network Infrastructure</option>
                  <option value="Fintech & Banking">Fintech & Banking</option>
                  <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                  <option value="Aerospace & Defense">Aerospace & Defense</option>
                  <option value="Software & Cloud Services">Software & Cloud Services</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1.5 font-medium">
                  PLAN TIER
                </label>
                <div className="flex items-center justify-between border border-accent/40 bg-accent/5 rounded px-3 py-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-accent" />
                    <span className="font-semibold text-accent">Enterprise MaaS Edition</span>
                  </div>
                  <span className="font-mono text-accent text-[11px] font-medium">Unlimited Silos</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 02: Head of Company */}
          <div className="space-y-4 pt-6 border-t border-border/60">
            <Eyebrow>02 / HEAD OF COMPANY (EXECUTIVE ADMIN)</Eyebrow>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field
                label="EXECUTIVE FULL NAME *"
                placeholder="e.g. Marcus Vance"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
              <Field
                label="OFFICIAL WORK EMAIL *"
                type="email"
                placeholder="admin@enterprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Field
                label="MASTER PASSWORD *"
                type="password"
                placeholder="••••••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                hint="Minimum 8 characters"
                required
              />
            </div>
          </div>

          {/* Section 03: Enterprise Departments */}
          <div className="space-y-4 pt-6 border-t border-border/60">
            <Eyebrow>03 / ENTERPRISE DEPARTMENTS SETUP</Eyebrow>
            <p className="text-xs text-muted-foreground">
              Configure initial departments for employee role mapping, incident scopes, and knowledge transfer domains.
            </p>

            {/* Department tags display */}
            <div className="flex flex-wrap gap-2 pt-1">
              {departments.map((dept) => (
                <div
                  key={dept}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-muted/60 border border-border text-xs text-foreground font-mono group hover:border-accent/40 transition-colors"
                >
                  <svg className="w-3.5 h-3.5 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                    <polyline points="9 22 9 12 15 12 15 22" />
                  </svg>
                  <span>{dept}</span>
                  <button
                    type="button"
                    onClick={() => removeDepartment(dept)}
                    className="text-muted-foreground hover:text-bad ml-1 transition-colors"
                    title="Remove department"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            {/* Add Custom Department Input */}
            <div className="flex gap-2 max-w-md pt-2">
              <input
                type="text"
                placeholder="Add custom department..."
                value={customDept}
                onChange={(e) => setCustomDept(e.target.value)}
                className="flex-1 bg-background border border-border rounded px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
              <button
                type="button"
                onClick={addDepartment}
                className="px-3 py-1.5 text-xs font-mono font-medium rounded border border-border hover:border-accent hover:text-accent transition-colors bg-muted/40"
              >
                + Add
              </button>
            </div>
          </div>

          {/* Action Row */}
          <div className="pt-6 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link
              href="/login"
              className="text-xs text-muted-foreground hover:text-accent transition-colors font-mono"
            >
              ← Already registered? Go to Login
            </Link>

            <Button
              type="submit"
              disabled={loading}
              className="w-full sm:w-auto px-6 py-2.5 bg-accent text-accent-foreground font-semibold rounded shadow-[0_0_20px_rgba(14,165,233,0.35)] hover:shadow-[0_0_25px_rgba(14,165,233,0.5)] transition-all flex items-center justify-center gap-2"
            >
              {loading ? 'Initializing Brain...' : 'Initialize Company Brain →'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

