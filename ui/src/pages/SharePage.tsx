import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../api/client'
import { LoadingSpinner } from '@mees/shared-ui'

export default function SharePage() {
  const { slug = '', memberId = '' } = useParams()

  const { data, isLoading, error } = useQuery({
    queryKey: ['share', slug, memberId],
    queryFn: () => apiFetch<any>(`/share/${slug}/${memberId}`),
    enabled: !!slug && !!memberId,
  })

  if (isLoading) return <LoadingSpinner className="mt-12" />
  if (error) return <p className="text-center text-text-secondary mt-12">Not found</p>
  if (!data) return null

  const { trip, member, balance, debts, expenses } = data

  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-text-primary mb-1">{trip.name}</h1>
      <h2 className="text-lg text-text-secondary mb-6">{member.name}</h2>

      {/* Balance */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
        <div className="text-sm text-text-secondary mb-1">Your balance</div>
        <div className={`text-2xl tabular-nums font-bold ${balance >= 0 ? 'text-positive' : 'text-negative'}`}>
          {trip.currency} {balance >= 0 ? '+' : ''}{balance.toFixed(2)}
        </div>
        <div className="text-xs text-text-secondary mt-1">
          {balance > 0 ? 'You are owed money' : balance < 0 ? 'You owe money' : 'All settled up'}
        </div>
      </div>

      {/* Debts */}
      {debts.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Actions needed</h3>
          <div className="space-y-2">
            {debts.map((d: any, i: number) => (
              <div key={i} className="text-sm text-text-primary">
                {d.from === member.name ? (
                  <>You need to pay <span className="font-medium">{d.to}</span> <span className="tabular-nums font-medium text-negative">{trip.currency} {d.amount.toFixed(2)}</span></>
                ) : (
                  <><span className="font-medium">{d.from}</span> owes you <span className="tabular-nums font-medium text-positive">{trip.currency} {d.amount.toFixed(2)}</span></>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expenses */}
      {expenses.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Your expenses</h3>
          <div className="space-y-2">
            {expenses.map((exp: any) => (
              <div key={exp.id} className="flex justify-between text-sm border-b border-border last:border-0 pb-2">
                <div>
                  <div className="text-text-primary">{exp.description}</div>
                  <div className="text-xs text-text-secondary">{exp.date} — paid by {exp.paid_by_name}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="tabular-nums text-text-primary">{exp.currency} {Number(exp.amount).toFixed(2)}</div>
                  <div className="tabular-nums text-xs text-text-secondary">your share: {exp.my_share.toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
