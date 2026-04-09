import { Link, NavLink } from 'react-router-dom'
import { AppSwitcher } from '@mees/shared-ui'
import { useTrips } from '../../hooks/useTrips'

interface SidebarProps {
  className?: string
  onNavigate?: () => void
}

export default function Sidebar({ className, onNavigate }: SidebarProps) {
  const { data: trips } = useTrips()

  return (
    <aside className={`w-52 bg-bg-secondary border-r border-border flex flex-col shrink-0 ${className ?? ''}`}>
      <div className="p-4 border-b border-border flex items-center justify-between">
        <Link to="/" className="text-lg font-bold text-accent hover:text-accent-hover transition-colors">Trips</Link>
        <AppSwitcher currentApp="Trips" />
      </div>
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {trips?.map((trip: { slug: string; name: string; active: boolean }) => (
          <NavLink
            key={trip.slug}
            to={`/trip/${trip.slug}`}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent/15 text-accent font-medium'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }`
            }
          >
            {trip.active && <span className="w-1.5 h-1.5 rounded-full bg-positive shrink-0" />}
            <span className="truncate">{trip.name}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
