import { useCallback, useEffect, useState, type FormEvent } from 'react'

type User = { username: string; role: string; enabled: boolean; enrolled: boolean }
export function Permissions({ token }: { token: string }) {
  const [users, setUsers] = useState<User[] | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('operator')
  const [enabled, setEnabled] = useState(true)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    const response = await fetch('/auth/users', { headers: { Authorization: `Bearer ${token}` } })
    if (response.ok) setUsers(await response.json())
  }, [token])
  useEffect(() => { void load().catch(() => setMessage('Habilitations indisponibles.')) }, [load])
  async function action(path: string, method: string, body?: object) {
    setBusy(true); setMessage('')
    try {
      const response = await fetch(path, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(25000) })
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Opération refusée.')
      setMessage('Habilitation mise à jour.'); setPassword(''); await load()
    } catch (e) { setMessage((e as Error).message) }
    finally { setBusy(false) }
  }
  function save(event: FormEvent) {
    event.preventDefault()
    void action('/auth/users', 'PUT', { username, role, enabled, ...(password ? { password } : {}) })
  }
  if (!users) return null
  return <section className="my-10 space-y-4 border-t border-slate-700 pt-6">
    <h2 className="text-xl font-semibold">Habilitations et reconnaissance faciale</h2>
    <p className="text-sm text-slate-400">Pour enrôler un visage, placez la personne devant la caméra USB du PC hôte pendant environ 18 secondes. Vérifiez physiquement son identité avant l’enrôlement.</p>
    <p role="status">{busy ? 'Opération en cours sur le PC hôte…' : message}</p>
    <ul className="space-y-3">{users.map(user => <li key={user.username} className="flex flex-wrap items-center gap-3">
      <span>{user.username} · {user.role} · {user.enabled ? 'actif' : 'désactivé'} · {user.enrolled ? 'visage enregistré' : 'visage à enrôler'}</span>
      <button disabled={busy} onClick={() => { setUsername(user.username); setRole(user.role); setEnabled(!!user.enabled); setPassword('') }}>Modifier</button>
      <button disabled={busy} onClick={() => void action(`/auth/users/${encodeURIComponent(user.username)}/enroll`, 'POST')}>Enrôler / remplacer</button>
      <button disabled={busy} onClick={() => { if (window.confirm(`Supprimer le compte et le modèle facial de ${user.username} ?`)) void action(`/auth/users/${encodeURIComponent(user.username)}`, 'DELETE') }}>Supprimer</button>
    </li>)}</ul>
    <form onSubmit={save} className="max-w-sm space-y-3">
      <label className="block">Compte<input value={username} onChange={e => setUsername(e.target.value)} pattern="[a-zA-Z0-9_.-]+" maxLength={64} required /></label>
      <label className="block">Nouveau mot de passe (requis pour créer)<input type="password" autoComplete="new-password" minLength={12} value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label className="block">Rôle<select value={role} onChange={e => setRole(e.target.value)}><option value="operator">Opérateur</option><option value="admin">Administrateur</option></select></label>
      <label className="flex items-center gap-2"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />Compte actif</label>
      <button disabled={busy}>Enregistrer les habilitations</button>
    </form>
  </section>
}
