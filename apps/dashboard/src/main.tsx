import { StrictMode, useCallback, useEffect, useState, type FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type Transaction = { id: string; amount_cents: number; currency: string; status: string; created_at: string }

function App() {
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('operator')
  const [password, setPassword] = useState('')
  const [amount, setAmount] = useState('10.00')
  const [status, setStatus] = useState('Vérification…')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  // Preserve the key when retrying an ambiguous network failure.
  const [pending, setPending] = useState<{ key: string; cents: number } | null>(null)

  const refresh = useCallback(async () => {
    try {
      const health = await fetch('/api/health', { signal: AbortSignal.timeout(4000) })
      setStatus(health.ok ? 'Service de paiement disponible' : 'Service de paiement indisponible')
    } catch { setStatus('Service de paiement injoignable') }
    if (token) {
      try {
        const response = await fetch('/api/transactions', {
          headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(4000),
        })
        if (response.status === 401) { setToken(''); setTransactions([]); return }
        if (!response.ok) throw new Error('Historique indisponible')
        setTransactions(await response.json())
      } catch { setError('Impossible de charger les transactions.') }
    }
  }, [token])

  useEffect(() => {
    void refresh()
    const interval = setInterval(() => void refresh(), 5000)
    return () => clearInterval(interval)
  }, [refresh])

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const response = await fetch('/auth/token', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }), signal: AbortSignal.timeout(10000),
      })
      if (!response.ok) throw new Error('Connexion refusée ou service indisponible.')
      setToken((await response.json()).access_token); setPassword('')
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  async function pay(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    const cents = pending?.cents ?? Math.round(Number(amount) * 100)
    const key = pending?.key ?? crypto.randomUUID()
    setPending({ cents, key })
    try {
      const response = await fetch('/api/transactions', {
        method: 'POST', headers: {
          'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'Idempotency-Key': key,
        },
        body: JSON.stringify({ amount_cents: cents, currency: 'EUR' }),
        signal: AbortSignal.timeout(10000),
      })
      if (!response.ok) throw new Error('Paiement non confirmé. Réessayez avec la même référence.')
      setPending(null)
      await refresh()
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  return <main className="mx-auto max-w-5xl px-6 py-12">
    <p className="text-sm uppercase tracking-widest text-cyan-300">EPSI · Workshop M2 · 2026</p>
    <h1 className="mt-3 text-4xl font-bold">Resilience Alpha</h1>
    <p className="mt-4 text-slate-400">Paiements fictifs et supervision du laboratoire.</p>
    <div className="my-8 border-y border-slate-700 py-5" role="status" aria-live="polite">{status}</div>
    <p className="mb-8 text-sm text-amber-200">Socle de développement : détection ML et reprise autonome à intégrer.</p>
    {error && <p role="alert" className="mb-6 text-rose-300">{error}</p>}
    {!token ? <form onSubmit={login} className="max-w-sm space-y-4">
      <h2 className="text-xl font-semibold">Connexion opérateur</h2>
      <label className="block">Identifiant<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required /></label>
      <label className="block">Mot de passe<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
      <button disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</button>
    </form> : <>
      <form onSubmit={pay} className="flex max-w-xl flex-wrap items-end gap-4">
        <label className="grow">Montant fictif (€)<input type="number" min="0.01" max="1000000" step="0.01" value={amount} disabled={!!pending} onChange={e => setAmount(e.target.value)} required /></label>
        <button disabled={busy}>{busy ? 'Traitement…' : pending ? 'Réessayer le paiement' : 'Créer un paiement'}</button>
      </form>
      <h2 className="mb-4 mt-12 text-xl font-semibold">Transactions récentes</h2>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <caption className="sr-only">100 dernières transactions de votre compte</caption>
        <thead className="text-slate-400"><tr><th className="py-3">Référence</th><th>Montant</th><th>État</th><th>Date</th></tr></thead>
        <tbody>{transactions.map(t => <tr key={t.id} className="border-t border-slate-800">
          <td className="py-4 font-mono">{t.id.slice(0, 8)}</td><td>{(t.amount_cents / 100).toFixed(2)} {t.currency}</td><td>{t.status}</td><td>{new Date(t.created_at).toLocaleString('fr-FR')}</td>
        </tr>)}</tbody>
      </table></div>
      {!transactions.length && <p className="mt-4 text-slate-400">Aucune transaction.</p>}
    </>}
  </main>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
