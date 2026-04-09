import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LoadingSpinner } from '@mees/shared-ui'
import {
  useTrip, useExpenses, useSettlements, useBalances,
  useAddExpense, useDeleteExpense, useAddSettlement,
  useAddMember, useSetActive,
} from '../hooks/useTrips'

const CURRENCIES = ['GBP', 'EUR', 'CHF', 'USD', 'PLN', 'NOK']

export default function TripPage() {
  const { slug = '' } = useParams()
  const { data: trip, isLoading } = useTrip(slug)
  const { data: expenses } = useExpenses(slug)
  const { data: settlements } = useSettlements(slug)
  const { data: balanceData } = useBalances(slug)

  if (isLoading) return <LoadingSpinner className="mt-12" />
  if (!trip) return <p className="text-text-secondary mt-8">Trip not found</p>

  const members = trip.members || []

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-text-primary">{trip.name}</h1>
        <span className="text-sm text-text-secondary">{trip.currency}</span>
        {!trip.active && <SetActiveButton slug={slug} />}
        {trip.active && (
          <span className="px-2 py-0.5 text-xs rounded bg-positive/15 text-positive font-medium">
            active (pipeline target)
          </span>
        )}
      </div>

      {/* Balances & Debts */}
      {balanceData && (
        <section className="bg-bg-card border border-border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-3">Balances</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
            {Object.entries(balanceData.balances).map(([id, b]: [string, any]) => (
              <div key={id} className="flex justify-between px-3 py-1.5 rounded bg-bg-primary text-sm">
                <Link
                  to={`/share/${slug}/${id}`}
                  className="text-text-primary hover:text-accent transition-colors"
                >
                  {b.name}
                </Link>
                <span className={`tabular-nums font-medium ${b.balance >= 0 ? 'text-positive' : 'text-negative'}`}>
                  {b.balance >= 0 ? '+' : ''}{b.balance.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
          {balanceData.debts.length > 0 && (
            <>
              <h3 className="text-sm font-medium text-text-secondary mb-2">Suggested payments</h3>
              <div className="space-y-1">
                {balanceData.debts.map((d: any, i: number) => (
                  <div key={i} className="text-sm text-text-primary">
                    <span className="font-medium">{d.from}</span>
                    {' owes '}
                    <span className="font-medium">{d.to}</span>
                    {' '}
                    <span className="tabular-nums font-medium text-negative">{trip.currency} {d.amount.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* Members */}
      <section className="bg-bg-card border border-border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Members</h2>
        <div className="flex flex-wrap gap-2 mb-3">
          {members.map((m: any) => (
            <span key={m.id} className="px-2 py-1 rounded bg-bg-primary text-sm text-text-primary">{m.name}</span>
          ))}
        </div>
        <AddMemberForm slug={slug} />
      </section>

      {/* Add expense */}
      <section className="bg-bg-card border border-border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Add Expense</h2>
        <AddExpenseForm slug={slug} members={members} defaultCurrency={trip.currency} />
      </section>

      {/* Expenses */}
      <section className="bg-bg-card border border-border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Expenses</h2>
        <ExpenseList slug={slug} expenses={expenses || []} />
      </section>

      {/* Settlements */}
      <section className="bg-bg-card border border-border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Record Settlement</h2>
        <AddSettlementForm slug={slug} members={members} defaultCurrency={trip.currency} />
        {settlements && settlements.length > 0 && (
          <div className="mt-4 space-y-1">
            {settlements.map((s: any) => (
              <div key={s.id} className="text-sm text-text-primary">
                {s.from_name} paid {s.to_name} — {s.currency} {Number(s.amount).toFixed(2)} ({s.date})
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function SetActiveButton({ slug }: { slug: string }) {
  const setActive = useSetActive(slug)
  return (
    <button
      onClick={() => setActive.mutate()}
      className="text-xs px-2 py-1 rounded border border-border text-text-secondary hover:text-accent hover:border-accent transition-colors"
    >
      Set active
    </button>
  )
}

function AddMemberForm({ slug }: { slug: string }) {
  const [name, setName] = useState('')
  const addMember = useAddMember(slug)

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) { addMember.mutate({ name: name.trim() }); setName('') } }} className="flex gap-2">
      <input
        type="text" placeholder="New member" value={name} onChange={(e) => setName(e.target.value)}
        className="flex-1 px-3 py-1.5 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
      />
      <button type="submit" className="px-3 py-1.5 rounded-md bg-accent text-white text-sm hover:bg-accent-hover transition-colors">Add</button>
    </form>
  )
}

function AddExpenseForm({ slug, members, defaultCurrency }: { slug: string; members: any[]; defaultCurrency: string }) {
  const [desc, setDesc] = useState('')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState(defaultCurrency)
  const [paidBy, setPaidBy] = useState(members[0]?.id || 0)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [involved, setInvolved] = useState<Set<number>>(new Set(members.map((m: any) => m.id)))
  const addExpense = useAddExpense(slug)

  const toggle = (id: number) => {
    const next = new Set(involved)
    if (next.has(id)) next.delete(id); else next.add(id)
    setInvolved(next)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!desc.trim() || !amount) return
    addExpense.mutate({
      description: desc.trim(), amount, currency, paid_by: paidBy,
      date, involved: [...involved],
    }, { onSuccess: () => { setDesc(''); setAmount('') } })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <input type="text" placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} required
          className="col-span-2 px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent" />
        <input type="number" step="0.01" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} required
          className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent" />
        <select value={currency} onChange={(e) => setCurrency(e.target.value)}
          className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm">
          {CURRENCIES.map(c => <option key={c}>{c}</option>)}
        </select>
        <select value={paidBy} onChange={(e) => setPaidBy(Number(e.target.value))}
          className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm">
          {members.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
          className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm" />
      </div>
      <div>
        <span className="text-xs text-text-secondary">Split between:</span>
        <div className="flex flex-wrap gap-2 mt-1">
          {members.map((m: any) => (
            <label key={m.id} className="flex items-center gap-1.5 text-sm text-text-primary cursor-pointer">
              <input type="checkbox" checked={involved.has(m.id)} onChange={() => toggle(m.id)}
                className="rounded border-border accent-accent" />
              {m.name}
            </label>
          ))}
        </div>
      </div>
      <button type="submit" disabled={addExpense.isPending}
        className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50">
        {addExpense.isPending ? 'Adding...' : 'Add Expense'}
      </button>
    </form>
  )
}

function ExpenseList({ slug, expenses }: { slug: string; expenses: any[] }) {
  const deleteExpense = useDeleteExpense(slug)

  if (!expenses.length) return <p className="text-sm text-text-secondary">No expenses yet.</p>

  return (
    <div className="space-y-2">
      {expenses.map((exp: any) => (
        <div key={exp.id} className="flex items-start justify-between gap-2 py-2 border-b border-border last:border-0">
          <div className="min-w-0">
            <div className="text-sm font-medium text-text-primary">{exp.description}</div>
            <div className="text-xs text-text-secondary">
              Paid by {exp.paid_by_name} — {exp.date}
              {exp.source === 'pipeline' && (
                <span className="ml-1 px-1 py-0.5 rounded bg-accent/10 text-accent text-[10px]">pipeline</span>
              )}
            </div>
            <div className="text-xs text-text-secondary mt-0.5">
              Split: {exp.shares?.map((s: any) => `${s.member_name} ${Number(s.amount).toFixed(2)}`).join(', ')}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="tabular-nums text-sm font-medium text-text-primary">
              {exp.currency} {Number(exp.amount).toFixed(2)}
            </span>
            <button
              onClick={() => { if (confirm('Delete this expense?')) deleteExpense.mutate(exp.id) }}
              className="text-xs text-text-secondary hover:text-negative transition-colors"
            >
              x
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

function AddSettlementForm({ slug, members, defaultCurrency }: { slug: string; members: any[]; defaultCurrency: string }) {
  const [from, setFrom] = useState(members[0]?.id || 0)
  const [to, setTo] = useState(members[1]?.id || 0)
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState(defaultCurrency)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const addSettlement = useAddSettlement(slug)

  return (
    <form onSubmit={(e) => {
      e.preventDefault()
      if (!amount) return
      addSettlement.mutate({ from_member: from, to_member: to, amount, currency, date },
        { onSuccess: () => setAmount('') })
    }} className="grid grid-cols-2 gap-3">
      <select value={from} onChange={(e) => setFrom(Number(e.target.value))}
        className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm">
        {members.map((m: any) => <option key={m.id} value={m.id}>{m.name} pays</option>)}
      </select>
      <select value={to} onChange={(e) => setTo(Number(e.target.value))}
        className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm">
        {members.map((m: any) => <option key={m.id} value={m.id}>to {m.name}</option>)}
      </select>
      <input type="number" step="0.01" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)}
        className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent" required />
      <select value={currency} onChange={(e) => setCurrency(e.target.value)}
        className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm">
        {CURRENCIES.map(c => <option key={c}>{c}</option>)}
      </select>
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
        className="px-3 py-2 rounded-md bg-bg-primary border border-border text-text-primary text-sm" />
      <button type="submit" disabled={addSettlement.isPending}
        className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50">
        Record
      </button>
    </form>
  )
}
