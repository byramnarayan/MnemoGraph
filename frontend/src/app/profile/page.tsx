'use client';

import React, { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api-client';
import { Button, Eyebrow, Field, Panel, Callout, Tag } from '@/kit';

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading: authLoading, refreshUser, logout } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [department, setDepartment] = useState(user?.department || '');
  const [industryVertical, setIndustryVertical] = useState(user?.industry_vertical || '');

  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [msg, setMsg] = useState<{ text: string; tone: 'ok' | 'bad' } | null>(null);

  React.useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    } else if (user) {
      setFullName(user.full_name || '');
      setCompanyName(user.company_name || '');
      setDepartment(user.department || '');
      setIndustryVertical(user.industry_vertical || '');
    }
  }, [user, authLoading, router]);

  if (authLoading || !user) {
    return (
      <div className="py-24 text-center">
        <span className="font-mono text-sm text-muted-foreground animate-pulse">
          Authenticating security session...
        </span>
      </div>
    );
  }

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);

    try {
      await api.users.updateProfile({
        full_name: fullName,
        company_name: companyName,
        department: department,
        industry_vertical: industryVertical,
      });
      await refreshUser();
      setMsg({ text: 'Profile successfully updated.', tone: 'ok' });
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to update profile.', tone: 'bad' });
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setMsg({ text: 'Avatar file size must be less than 5MB.', tone: 'bad' });
      return;
    }

    setUploadingAvatar(true);
    setMsg(null);
    try {
      await api.users.uploadAvatar(file);
      await refreshUser();
      setMsg({ text: 'Profile picture uploaded to S3 successfully!', tone: 'ok' });
    } catch (err: any) {
      setMsg({ text: err.message || 'S3 upload failed.', tone: 'bad' });
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleDeleteAvatar = async () => {
    if (!confirm('Are you sure you want to revert to default avatar?')) return;
    setUploadingAvatar(true);
    setMsg(null);
    try {
      await api.users.deleteAvatar();
      await refreshUser();
      setMsg({ text: 'Reverted to default avatar.', tone: 'ok' });
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to delete avatar.', tone: 'bad' });
    } finally {
      setUploadingAvatar(false);
    }
  };

  return (
    <div className="py-12 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/80 pb-6">
        <div>
          <Eyebrow>RBAC PROFILE & IDENTITY</Eyebrow>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Account & Executive Brain Settings
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Manage your personal profile, credentials, and S3 enterprise assets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Tag tone="accent">{user.role}</Tag>
          <Button variant="ghost" onClick={logout} className="text-xs">
            Sign Out
          </Button>
        </div>
      </div>

      {msg && (
        <Callout tone={msg.tone} title={msg.tone === 'ok' ? 'Success' : 'Error'}>
          {msg.text}
        </Callout>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Column: Avatar & S3 Card */}
        <div className="space-y-6">
          <Panel title="Profile Avatar (AWS S3)">
            <div className="p-6 flex flex-col items-center text-center space-y-4">
              <div className="relative group">
                <img
                  src={user.image_url}
                  alt={user.full_name}
                  className="w-32 h-32 rounded-full object-cover border-2 border-border shadow-lg group-hover:border-accent transition-colors"
                />
                {uploadingAvatar && (
                  <div className="absolute inset-0 rounded-full bg-background/80 flex items-center justify-center font-mono text-xs text-accent">
                    Syncing...
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <p className="font-semibold text-sm">{user.full_name}</p>
                <p className="text-xs text-muted-foreground font-mono">{user.email}</p>
                <p className="text-[10px] text-muted-foreground font-mono">
                  {user.image_file ? `S3 Key: ${user.image_file.slice(0, 16)}...` : 'Using Default Avatar'}
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleAvatarChange}
              />

              <div className="flex flex-col gap-2 w-full pt-2">
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingAvatar}
                  className="w-full text-xs"
                >
                  {uploadingAvatar ? 'Uploading to S3...' : 'Upload New Photo'}
                </Button>

                {user.image_file && (
                  <Button
                    variant="ghost"
                    onClick={handleDeleteAvatar}
                    disabled={uploadingAvatar}
                    className="w-full text-xs text-bad hover:text-bad"
                  >
                    Remove Photo
                  </Button>
                )}
              </div>
            </div>
          </Panel>

          <Panel title="Tenant Metadata">
            <div className="p-4 space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">Tenant Slug:</span>
                <span className="text-accent">{user.tenant_slug || 'default_tenant'}</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">Account Status:</span>
                <span className="text-ok">Active Verified</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created:</span>
                <span>{new Date(user.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </Panel>
        </div>

        {/* Right Column: Profile Edit Form */}
        <div className="md:col-span-2">
          <Panel title="Executive Details">
            <form onSubmit={handleUpdateProfile} className="p-6 space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field
                  label="FULL NAME"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1.5 font-medium">
                    OFFICIAL WORK EMAIL
                  </label>
                  <input
                    type="email"
                    value={user.email}
                    disabled
                    className="w-full bg-muted/40 border border-border rounded px-3 py-2 text-sm text-muted-foreground cursor-not-allowed font-mono"
                  />
                  <span className="text-[10px] text-muted-foreground/70 font-mono mt-1 block">
                    Contact admin to update master identity email.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field
                  label="COMPANY / ORGANIZATION"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
                <Field
                  label="PRIMARY DEPARTMENT"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                />
              </div>

              <div>
                <Field
                  label="INDUSTRY VERTICAL"
                  value={industryVertical}
                  onChange={(e) => setIndustryVertical(e.target.value)}
                />
              </div>

              <div className="pt-4 border-t border-border flex justify-end">
                <Button type="submit" disabled={saving} className="px-6">
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </Panel>
        </div>
      </div>
    </div>
  );
}

