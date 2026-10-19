import { useEffect, useState, type FormEvent } from 'react'

type Timeline = { timestamp: number; state: string; detail: Record<string, unknown> }
type Incident = {
  id: string; source_ip: string; state: string; created_at: number; updated_at: number;
  evidence: { score: number; threshold: number; model_version: string };
  timeline: Timeline[];
}
type Status = {
  model: { algorithm: string; version: string; train_windows: number; validation_windows: number } | null;
  last_cycle: number; last_error: string | null; loki_error: string | null;
  events_collected: number;
  soc_last_minute: { service: string; status: number; count: number }[];
  incidents: Incident[];
}
type Answer = {
  answer: string; mode: string; model?: string;
  sources: { source: string; chunk: number; score: number; excerpt: string }[];
}
const states: Record<string, string> = {
  detected: 'Anomalie détectée', recovering: 'Mise en quarantaine', verifying: 'Vérification métier',
  recovered: 'Service rétabli et paiement vérifié', failed: 'Échec de reprise',
}

export function Operations({ token }: { token: string }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [question, setQuestion] = useState('Comment vérifier la reprise après une quarantaine ?')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let stopped = false
    async function refresh() {
      try {
        const response = await fetch('/control/status', {
          headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(5000),
        })
        if (!response.ok) throw new Error('Supervision indisponible')
        const body = await response.json()
        if (!stopped) { setStatus(body); setError('') }
      } catch { if (!stopped) setError('Supervision indisponible. Les informations affichées peuvent être anciennes.') }
    }
    void refresh()
    const timer = setInterval(() => void refresh(), 2000)
    return () => { stopped = true; clearInterval(timer) }
  }, [token])

  async function ask(event: FormEvent) {
    event.preventDefault(); setBusy(true); setAnswer(null)
    try {
      const response = await fetch('/assistant/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question }), signal: AbortSignal.timeout(100000),
      })
      if (!response.ok) throw new Error('Assistant indisponible')
      setAnswer(await response.json())
    } catch { setAnswer({ answer: 'Impossible de joindre l’assistant local.', mode: 'error', sources: [] }) }
    finally { setBusy(false) }
  }

  return <section className="mt-12 border-t border-slate-700 pt-8">
    <h2 className="text-2xl font-semibold">Supervision et reprise autonome</h2>
    {error && <p role="alert" className="my-4 text-rose-300">{error}</p>}
    {status && <>
      <div className="my-6 flex flex-wrap gap-x-10 gap-y-3 text-sm text-slate-300">
        <p>Détection : {status.model ? `${status.model.algorithm} · ${status.model.version.slice(0, 8)}` : 'En attente de calibration'}</p>
        <p>{status.events_collected.toLocaleString('fr-FR')} événements collectés</p>
        <p>Dernier cycle : {new Date(status.last_cycle * 1000).toLocaleTimeString('fr-FR')}</p>
      </div>
      {status.last_error && <p className="text-rose-300">Erreur du détecteur : {status.last_error}</p>}
      {status.loki_error && <p className="text-amber-200">Envoi Loki en attente : {status.loki_error}</p>}
      <p className="text-sm text-slate-400">SOC, dernière minute : {status.soc_last_minute.map(s => `${s.service} HTTP ${s.status} × ${s.count}`).join(' · ') || 'Aucun événement'}</p>
      <div className="mt-6 space-y-6" aria-live="polite">
        {!status.incidents.length && <p>Aucun incident détecté.</p>}
        {status.incidents.slice(0, 1).map(incident => <article key={incident.id} className="border-l-2 border-cyan-300 pl-5">
          <h3 className={`font-semibold ${incident.state === 'failed' ? 'text-rose-300' : 'text-cyan-200'}`}>{states[incident.state] ?? incident.state}</h3>
          <p className="my-2 text-sm text-slate-400">Source {incident.source_ip} · {((incident.updated_at - incident.created_at)).toFixed(1)} s depuis la détection · score {incident.evidence.score.toFixed(3)}</p>
          <ol className="space-y-2 text-sm">{incident.timeline.map((event, index) => <li key={index}>
            <time className="mr-3 font-mono text-slate-400">{new Date(event.timestamp * 1000).toLocaleTimeString('fr-FR')}</time>
            {states[event.state] ?? event.state}
            {typeof event.detail.transaction_id === 'string' && <span className="ml-2 text-emerald-300">Transaction {event.detail.transaction_id.slice(0, 8)}</span>}
            {typeof event.detail.reason === 'string' && <span className="ml-2 text-rose-300">{event.detail.reason}</span>}
          </li>)}</ol>
          <details className="mt-3 text-sm"><summary className="cursor-pointer text-slate-400">Preuves techniques</summary><pre className="mt-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(incident, null, 2)}</pre></details>
        </article>)}
        {status.incidents.length > 1 && <details className="text-sm">
          <summary className="cursor-pointer text-slate-400">Historique : {status.incidents.length - 1} incidents précédents</summary>
          <ul className="mt-3 space-y-2">{status.incidents.slice(1).map(incident => <li key={incident.id}>
            {new Date(incident.created_at * 1000).toLocaleString('fr-FR')} · {incident.source_ip} · {states[incident.state] ?? incident.state}
          </li>)}</ul>
        </details>}
      </div>
    </>}
    <form onSubmit={ask} className="mt-10 space-y-3">
      <h3 className="text-xl font-semibold">Assistant documentaire local</h3>
      <label className="block">Question<input minLength={5} maxLength={1000} value={question} onChange={e => setQuestion(e.target.value)} required /></label>
      <button disabled={busy}>{busy ? 'Recherche dans les procédures…' : 'Consulter les procédures'}</button>
    </form>
    {answer && <div className="mt-5">
      <p className="mb-2 text-sm text-slate-400">{answer.mode === 'rag' ? `Réponse RAG · ${answer.model}` : `Mode : ${answer.mode}`}</p>
      <p className="whitespace-pre-wrap">{answer.answer}</p>
      {answer.sources.map((source, i) => <details key={i} className="mt-3 text-sm">
        <summary className="cursor-pointer text-cyan-200">[{i + 1}] {source.source}</summary>
        <p className="mt-2 whitespace-pre-wrap text-slate-300">{source.excerpt}</p>
      </details>)}
    </div>}
  </section>
}
