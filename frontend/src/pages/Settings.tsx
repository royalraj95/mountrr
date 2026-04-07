import {useQuery, useQueryClient} from '@tanstack/react-query'
import {Save} from 'lucide-react'
import {useEffect, useState} from 'react'
import type {Settings} from '@/lib/api'
import {api} from '@/lib/api'

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState<Partial<Settings>>({})

  const { data } = useQuery({
    queryKey: ['settings'],
    queryFn: api.settings.get,
  })

  useEffect(() => {
    if (data) setForm(data)
  }, [data])

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setSaved(false)
    try {
      await api.settings.update(form)
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  if (!data) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 w-32 bg-muted rounded animate-pulse" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  const inputClass =
    'w-full px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring'

  return (
    <div className="p-6 max-w-2xl space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>

      {saved && (
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 px-4 py-2 text-sm">
          Settings saved.
        </div>
      )}

      {/* Scan */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b border-border pb-2">Scanning</h2>

        <Field
          label="Scan Interval (minutes)"
          hint="How often to automatically scan for broken symlinks. Set to 0 to disable automatic scans."
        >
          <input
            type="number"
            min={0}
            className={inputClass}
            value={form.scan_interval_minutes ?? 720}
            onChange={(e) => update('scan_interval_minutes', parseInt(e.target.value) || 0)}
          />
        </Field>

        <Field label="Dry Run Mode" hint="When enabled, no files will be deleted. Operations are logged only.">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.dry_run ?? false}
              onChange={(e) => update('dry_run', e.target.checked)}
              className="rounded border-input w-4 h-4"
            />
            <span className="text-sm">Enable dry run</span>
          </label>
        </Field>
      </section>

      {/* Mounts */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b border-border pb-2">Mount Paths</h2>

        <Field label="Real-Debrid Mount Path" hint="Container path where the RD rclone/WebDAV mount is mapped.">
          <input
            type="text"
            className={inputClass}
            value={form.rd_mount_path ?? '/mnt/rd'}
            onChange={(e) => update('rd_mount_path', e.target.value)}
          />
        </Field>

        <Field label="NzbDAV Mount Path" hint="Container path where the NzbDAV WebDAV mount is mapped.">
          <input
            type="text"
            className={inputClass}
            value={form.nzb_mount_path ?? '/mnt/nzb'}
            onChange={(e) => update('nzb_mount_path', e.target.value)}
          />
        </Field>
      </section>

      {/* Classification patterns */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b border-border pb-2">Classification Patterns</h2>

        <Field
          label="Real-Debrid Patterns"
          hint="Comma-separated substrings. A symlink target matching any of these is classified as 'rd'."
        >
          <input
            type="text"
            className={inputClass}
            value={(form.rd_patterns ?? []).join(', ')}
            onChange={(e) =>
              update(
                'rd_patterns',
                e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
              )
            }
          />
        </Field>

        <Field
          label="NzbDAV Patterns"
          hint="Comma-separated substrings. A symlink target matching any of these is classified as 'nzb'."
        >
          <input
            type="text"
            className={inputClass}
            value={(form.nzb_patterns ?? []).join(', ')}
            onChange={(e) =>
              update(
                'nzb_patterns',
                e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
              )
            }
          />
        </Field>

        <Field
          label="Media Directories"
          hint="Comma-separated container paths to scan for symlinks."
        >
          <input
            type="text"
            className={inputClass}
            value={(form.media_dirs ?? []).join(', ')}
            onChange={(e) =>
              update(
                'media_dirs',
                e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
              )
            }
          />
        </Field>
      </section>

      {/* Advanced */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold border-b border-border pb-2">Advanced</h2>

        <Field label="Log Level">
          <select
            className={inputClass}
            value={form.log_level ?? 'INFO'}
            onChange={(e) => update('log_level', e.target.value)}
          >
            <option>DEBUG</option>
            <option>INFO</option>
            <option>WARNING</option>
            <option>ERROR</option>
          </select>
        </Field>
      </section>

      {/* Arr — v1.1 notice */}
      <section className="space-y-2 opacity-60">
        <h2 className="text-base font-semibold border-b border-border pb-2">
          Arr Integration <span className="text-xs font-normal text-muted-foreground ml-2">v1.1</span>
        </h2>
        <p className="text-sm text-muted-foreground">
          Radarr and Sonarr auto-search on broken-symlink cleanup is coming in v1.1.
        </p>
      </section>
    </div>
  )
}
