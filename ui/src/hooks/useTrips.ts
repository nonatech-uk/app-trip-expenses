import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../api/client'

export function useTrips() {
  return useQuery({
    queryKey: ['trips'],
    queryFn: () => apiFetch<any[]>('/trips'),
  })
}

export function useTrip(slug: string) {
  return useQuery({
    queryKey: ['trip', slug],
    queryFn: () => apiFetch<any>(`/trips/${slug}`),
    enabled: !!slug,
  })
}

export function useBalances(slug: string) {
  return useQuery({
    queryKey: ['balances', slug],
    queryFn: () => apiFetch<{ balances: Record<string, any>; debts: any[] }>(`/trips/${slug}/balances`),
    enabled: !!slug,
  })
}

export function useExpenses(slug: string) {
  return useQuery({
    queryKey: ['expenses', slug],
    queryFn: () => apiFetch<any[]>(`/trips/${slug}/expenses`),
    enabled: !!slug,
  })
}

export function useSettlements(slug: string) {
  return useQuery({
    queryKey: ['settlements', slug],
    queryFn: () => apiFetch<any[]>(`/trips/${slug}/settlements`),
    enabled: !!slug,
  })
}

export function useCreateTrip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; currency: string; members: string[] }) =>
      apiFetch<{ id: number; slug: string }>('/trips', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trips'] }),
  })
}

export function useAddExpense(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      description: string
      amount: string
      currency: string
      paid_by: number
      date?: string
      involved?: number[]
    }) =>
      apiFetch<{ id: number }>(`/trips/${slug}/expenses`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses', slug] })
      qc.invalidateQueries({ queryKey: ['balances', slug] })
    },
  })
}

export function useDeleteExpense(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (expenseId: number) =>
      apiFetch<{ status: string }>(`/trips/${slug}/expenses/${expenseId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses', slug] })
      qc.invalidateQueries({ queryKey: ['balances', slug] })
    },
  })
}

export function useAddSettlement(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      from_member: number
      to_member: number
      amount: string
      currency: string
      date?: string
    }) =>
      apiFetch<{ id: number }>(`/trips/${slug}/settlements`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settlements', slug] })
      qc.invalidateQueries({ queryKey: ['balances', slug] })
    },
  })
}

export function useAddMember(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string }) =>
      apiFetch<{ id: number }>(`/trips/${slug}/members`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trip', slug] }),
  })
}

export function useUpdateFx(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { fx_rates: Record<string, number> }) =>
      apiFetch<{ status: string }>(`/trips/${slug}/fx`, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['trip', slug] })
      qc.invalidateQueries({ queryKey: ['balances', slug] })
    },
  })
}

export function useSetActive(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string }>(`/trips/${slug}/active`, { method: 'PUT' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trips'] }),
  })
}
