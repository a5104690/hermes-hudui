import { useApi } from '../hooks/useApi'
import Panel from './Panel'
import { useTranslation } from '../i18n'

function UsageBar({ label, item }: { label: string; item: any }) {
  if (!item) return null
  const value = Math.max(0, Math.min(100, Number(item.used_percent || 0)))
  const color = value >= 90 ? 'var(--hud-error)' : value >= 70 ? 'var(--hud-warning)' : 'var(--hud-primary)'
  return (
    <div className="mb-2">
      <div className="flex justify-between text-[12px] mb-1">
        <span style={{ color: 'var(--hud-text-dim)' }}>{label}</span>
        <span className="font-bold tabular-nums" style={{ color }}>{value}%</span>
      </div>
      <div className="h-[6px]" style={{ background: 'var(--hud-bg-hover)' }}>
        <div style={{ width: `${value}%`, height: '100%', background: color }} />
      </div>
      {item.reset_text && <div className="text-[11px] mt-0.5" style={{ color: 'var(--hud-text-dim)' }}>{item.reset_text}</div>}
    </div>
  )
}

export default function ClaudeUsagePanel() {
  const { t } = useTranslation()
  const { data, error, mutate } = useApi('/claude-usage', 60000)
  const { data: agents } = useApi('/agents', 15000)

  const refresh = async () => {
    await fetch('/api/claude-usage/refresh', { method: 'POST' })
    await mutate()
  }

  const status = data?.status || (error ? 'error' : 'loading')
  const statusColor = status === 'fresh' ? 'var(--hud-success)' : status === 'stale' ? 'var(--hud-warning)' : 'var(--hud-text-dim)'
  const statusLabel = status === 'fresh' ? t('dashboard.claudeFresh') : status === 'stale' ? t('dashboard.claudeStale') : status === 'not_configured' ? t('dashboard.claudeNotConfigured') : status === 'reauth_required' ? t('dashboard.claudeReauth') : status === 'loading' ? t('dashboard.claudeLoading') : t('dashboard.claudeError')
  const processByName = new Map((agents?.processes || []).map((proc: any) => [proc.name, proc]))
  const workers = [
    { key: 'claude', label: 'Claude Code' },
    { key: 'agy', label: 'agy / Gemini' },
  ]

  return (
    <Panel title={t('dashboard.claudeUsage')}>
      <div className="flex items-center justify-between mb-3 text-[12px]">
        <span className="font-bold" style={{ color: 'var(--hud-text)' }}>Claude Pro / Claude Code</span>
        <span style={{ color: statusColor }}>● {statusLabel}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        {workers.map((worker) => {
          const proc: any = processByName.get(worker.key)
          const running = Boolean(proc?.running)
          return (
            <div key={worker.key} className="px-2 py-1.5 border" style={{ borderColor: 'var(--hud-border)', background: 'var(--hud-bg-panel)' }}>
              <div className="text-[11px]" style={{ color: 'var(--hud-text-dim)' }}>{worker.label}</div>
              <div className="text-[12px] font-bold" style={{ color: running ? 'var(--hud-success)' : 'var(--hud-text-dim)' }}>
                {running ? `● ${t('dashboard.agentWorking')}` : `○ ${t('dashboard.agentIdle')}`}
                {proc?.pid ? ` [${proc.pid}]` : ''}
              </div>
            </div>
          )
        })}
      </div>
      {data?.current_window || data?.weekly ? (
        <>
          <UsageBar label={t('dashboard.claudeFiveHour')} item={data.current_window} />
          <div className="pt-2 mt-2" style={{ borderTop: '1px solid var(--hud-border)' }}>
            <div className="text-[11px] uppercase tracking-widest mb-2" style={{ color: 'var(--hud-text-dim)' }}>{t('dashboard.claudeWeekly')}</div>
            <UsageBar label={t('dashboard.claudeAllModels')} item={data.weekly?.all_models} />
            <UsageBar label={t('dashboard.claudeFable')} item={data.weekly?.fable} />
          </div>
          <div className="text-[11px] mt-2" style={{ color: 'var(--hud-text-dim)' }}>
            {data.fetched_at ? `${t('dashboard.claudeUpdated')} ${new Date(data.fetched_at).toLocaleTimeString()}` : ''}
          </div>
        </>
      ) : (
        <div className="text-[12px] mb-3" style={{ color: 'var(--hud-text-dim)' }}>
          {data?.error || t('dashboard.claudeOpenUsage')}
        </div>
      )}
      <button
        className="mt-2 px-2 py-1 text-[11px] border"
        style={{ borderColor: 'var(--hud-border)', color: 'var(--hud-primary)', background: 'var(--hud-bg-panel)' }}
        onClick={refresh}
      >
        {t('dashboard.claudeRefresh')}
      </button>
    </Panel>
  )
}
