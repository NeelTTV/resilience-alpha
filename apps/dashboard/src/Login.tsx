import { useEffect, useState, type FormEvent } from 'react'

type State = { phase: string; remaining: number; blocked_seconds: number }
const labels: Record<string, string> = {
  camera: 'Caméra USB du PC hôte activée. Présentez votre visage devant cette caméra.',
  password: 'Visage reconnu. LED verte clignotante : saisissez votre mot de passe.',
  face_rejected: 'Visage non reconnu. LED rouge fixe pendant 30 secondes.',
  password_rejected: 'Mot de passe incorrect. La LED rouge clignote 10 fois.',
  success: 'Mot de passe validé. LED verte fixe : ouverture après 30 secondes.',
}

export function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [challenge, setChallenge] = useState('')
  const [state, setState] = useState<State | null>(null)
  const [blockedUntil, setBlockedUntil] = useState(0)
  const [now, setNow] = useState(Date.now())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!challenge) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const response = await fetch(`/auth/session/${challenge}`, { cache: 'no-store', signal: AbortSignal.timeout(5000) })
        if (!response.ok) {
          if (response.status === 404 && !stopped) {
            setChallenge(''); setUsername(''); setPassword(''); setState(null)
          }
          throw new Error('Identification expirée ou indisponible. Recommencez.')
        }
        const next: State = await response.json()
        if (stopped) return
        setState(next)
        if (next.phase.endsWith('rejected')) { setUsername(''); setPassword('') }
        if (next.blocked_seconds) setBlockedUntil(Date.now() + next.blocked_seconds * 1000)
        if (next.phase === 'done') {
          const complete = await fetch(`/auth/session/${challenge}/complete`, { method: 'POST', signal: AbortSignal.timeout(5000) })
          if (!complete.ok) throw new Error('Habilitation refusée ou session déjà utilisée.')
          const result = await complete.json()
          if (!stopped) { setChallenge(''); onLogin(result.access_token) }
          return
        }
        if (next.phase === 'failed') {
          setChallenge(''); setUsername(''); setPassword(''); setState(null)
          setError('Identification terminée ou expirée. Recommencez le parcours complet.')
          return
        }
      } catch (e) {
        if (stopped) return
        setError((e as Error).message)
      }
      if (!stopped) timer = setTimeout(() => void poll(), 500)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [challenge, onLogin])

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const response = await fetch(challenge ? '/auth/token' : '/auth/identify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(challenge ? { username, password, challenge } : { username }),
        signal: AbortSignal.timeout(10000),
      })
      if (!response.ok) {
        const retry = Number(response.headers.get('Retry-After'))
        if (response.status === 429 && retry) setBlockedUntil(Date.now() + retry * 1000)
        const result = await response.json()
        throw new Error(typeof result.detail === 'string' ? result.detail : 'Identification refusée.')
      }
      const result = await response.json()
      if (challenge) {
        setPassword(''); setState({ ...result, blocked_seconds: 0 })
        if (result.phase === 'password_rejected') setUsername('')
      } else {
        setChallenge(result.challenge); setState({ phase: 'camera', remaining: 35, blocked_seconds: 0 })
      }
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  const blocked = Math.max(0, Math.ceil((blockedUntil - now) / 1000))
  return <form onSubmit={submit} className="max-w-lg space-y-4">
    <h2 className="text-xl font-semibold">Connexion au back-office</h2>
    <p className="text-sm text-slate-400">Identifiant → visage sur le PC hôte → mot de passe → accès.</p>
    {error && <p role="alert" className="text-rose-300">{error}</p>}
    {blocked > 0 && <p role="status" className="text-amber-200">Blocage : {blocked} s avant un nouvel essai.</p>}
    <label className="block">Identifiant<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} disabled={!!challenge || blocked > 0} pattern="[a-zA-Z0-9_.-]+" maxLength={64} required /></label>
    {state && <p role="status" aria-live="polite">{labels[state.phase] || 'Vérification…'} {Math.ceil(state.remaining)} s</p>}
    {state?.phase === 'password' && <label className="block">Mot de passe<input autoFocus type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>}
    {(!challenge || state?.phase === 'password') && <button disabled={busy || blocked > 0}>{busy ? 'Vérification…' : challenge ? 'Valider le mot de passe' : 'Vérifier mon visage'}</button>}
  </form>
}
