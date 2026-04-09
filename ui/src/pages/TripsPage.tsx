import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTrips, useCreateTrip } from '../hooks/useTrips'
import { LoadingSpinner } from '@mees/shared-ui'

const CURRENCIES = ['GBP', 'EUR', 'CHF', 'USD', 'PLN', 'NOK']

export default function TripsPage() {
  const { data: trips, isLoading } = useTrips()
  const createTrip = useCreateTrip()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('GBP')
  const [members, setMembers] = useState('')

  if (isLoading) return <LoadingSpinner className="mt-12" />

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    const memberList = members.split(',').map(m => m.trim()).filter(Boolean)
    createTrip.mutate({ name: name.trim(), currency, members: memberList }, {
      onSuccess: (data) => navigate(`/trip/${data.slug}`),
    })
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-text-primary mb-6">Trips</h1>

      {/* Trip list */}
      <div className="space-y-2 mb-8">
        {trips?.map((trip: any) => (
          <a
            key={trip.slug}
            href={`/trip/${trip.slug}`}
            onClick={(e) => { e.preventDefault(); navigate(`/trip/${trip.slug}`) }}
            className="block bg-bg-card border border-border rounded-lg p-4 hover:bg-bg-hover transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-medium text-text-primary">{trip.name}</span>
                {trip.active && (
                  <span className="ml-2 inline-block px-1.5 py-0.5 text-[10px] rounded bg-positive/15 text-positive font-medium">
                    active
                  </span>
                )}
              </div>
              <span className="text-sm text-text-secondary">
                {trip.member_count} members, {trip.expense_count} expenses
              </span>
            </div>
          </a>
        ))}
        {trips?.length === 0 && (
          <p className="text-text-secondary text-sm">No trips yet. Create one below.</p>
        )}
      </div>

      {/* Create trip form */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h2 className="text-lg font-semibold text-text-primary mb-3">New Trip</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <input
            type="text"
            placeholder="Trip name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
            required
          />
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm"
          >
            {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input
            type="text"
            placeholder="Members (comma-separated)"
            value={members}
            onChange={(e) => setMembers(e.target.value)}
            className="w-full px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <button
            type="submit"
            disabled={createTrip.isPending}
            className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {createTrip.isPending ? 'Creating...' : 'Create Trip'}
          </button>
        </form>
      </div>
    </div>
  )
}
