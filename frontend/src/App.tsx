import {useEffect, useState} from 'react'
import {BrowserRouter, NavLink, Route, Routes} from 'react-router-dom'
import {useQueryClient} from '@tanstack/react-query'
import {HardDrive, History, LayoutDashboard, Link2, Moon, Settings, Sun} from 'lucide-react'
import {useEventStream} from '@/lib/sse'
import Dashboard from '@/pages/Dashboard'
import Symlinks from '@/pages/Symlinks'
import DeletionHistory from '@/pages/DeletionHistory'
import SettingsPage from '@/pages/Settings'
import {cn} from '@/lib/utils'

function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved !== 'light'
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    document.documentElement.classList.toggle('light', !dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return (
    <button
      onClick={() => setDark((d) => !d)}
      className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  )
}

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/symlinks', icon: Link2, label: 'Symlinks' },
  { to: '/history', icon: History, label: 'History' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function Sidebar() {
  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-border bg-card h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
        <HardDrive className="w-5 h-5 text-primary" />
        <span className="font-bold text-lg tracking-tight">Mountrr</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent',
              )
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Theme toggle */}
      <div className="p-3 border-t border-border flex justify-end">
        <ThemeToggle />
      </div>
    </aside>
  )
}

function EventListener() {
  const queryClient = useQueryClient()

  useEventStream((event) => {
    if (event.event === 'scan.completed' || event.event === 'scan.progress') {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['symlinks'] })
      queryClient.invalidateQueries({ queryKey: ['scan-status'] })
    }
    if (event.event === 'symlink.deleted') {
      queryClient.invalidateQueries({ queryKey: ['symlinks'] })
      queryClient.invalidateQueries({ queryKey: ['deletions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    }
    if (event.event === 'mount.health_changed') {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    }
  })

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <EventListener />
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/symlinks" element={<Symlinks />} />
            <Route path="/history" element={<DeletionHistory />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
