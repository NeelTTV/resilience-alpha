// Optional artifact authoring: use the supplied Codex primary runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const runtime = process.env.RUNTIME_NODE_MODULES;
const skill = process.env.PRESENTATIONS_SKILL_DIR;
if (!runtime || !skill) throw new Error('Set RUNTIME_NODE_MODULES and PRESENTATIONS_SKILL_DIR');
const requireRuntime = createRequire(path.join(runtime, '__runtime__.cjs'));
const { Presentation, PresentationFile } = await import(
  pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href,
);
const project = JSON.parse(await fs.readFile(path.join(root, 'project.json'), 'utf8'));
const recovery = JSON.parse(await fs.readFile(path.join(root, 'output/evidence/recovery.json'), 'utf8'));
if (!recovery.passed) throw new Error('Passing recovery proof required');
const incident = recovery.incident;
const seconds = (incident.updated_at - incident.created_at).toFixed(1);
const proof = incident.timeline.find(e => e.state === 'recovered').detail;
const output = path.join(root, 'output', project.delivery_slug);
const revision = process.env.DELIVERY_REVISION ?? '';
const temp = path.join(root, 'tmp/presentation');
await fs.mkdir(output, { recursive: true });
await fs.mkdir(temp, { recursive: true });
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function text(slide, content, left, top, width, height, fontSize = 30, bold = false, color = '#261E48') {
  const box = slide.shapes.add({
    geometry: 'textbox', position: { left, top, width, height }, fill: 'none',
    line: { fill: 'none', width: 0, style: 'solid' },
  });
  box.text = content;
  box.text.style = { typeface: 'Arial', fontSize, bold, color };
  box.text.insets = 0;
  return box;
}
function slide(title, notes) {
  const page = presentation.slides.add();
  page.background.fill = '#E4E6F3';
  text(page, title, 76, 62, 1128, 100, 46, true);
  page.speakerNotes.text = notes;
  return page;
}

let page = slide('RESILIENCE-ALPHA',
  'Ethan: I am Ethan DIVET, responsible for development. Present the fictitious payment path. '
  + 'Source: repository, docs/team.md and supplied EPSI workshop subject. No real financial data.');
text(page, 'Reprise autonome\nd’un paiement fictif', 76, 232, 1120, 180, 58, true);
text(page, 'Équipe DIVET · EPSI M2 · 19 octobre 2026', 76, 494, 1120, 56, 27);
text(page, 'Recette locale en conteneurs. Essai sur deux PC physiques à finaliser.', 76, 610, 1120, 52, 23);

page = slide('Architecture du démonstrateur',
  'Josselin: I am Josselin LENAOUR, responsible for infrastructure. Explain each container and '
  + 'the control network. Source: compose.yaml, infra/ansible/quarantine.yml, docs/architecture.md.');
text(page, 'WAF et interface\nAuthentification dédiée et API de paiement\nPostgreSQL et volumes persistants', 76, 205, 1120, 210, 36);
text(page, 'Prometheus, Grafana et Loki rendent l’incident observable.\nLe superviseur pilote un exécuteur Ansible isolé.\nAucun service applicatif ne reçoit le socket Docker.', 76, 454, 1120, 170, 28);

page = slide('Saturation applicative contrôlée',
  'Maxime: I am Maxime DUSSORT, responsible for cybersecurity. Explain scope and quotas. '
  + 'Source: security/scenarios/request_flood.py and output/evidence/recovery.json. '
  + 'The quota is deliberately small for this lab. This is not a discovered payment-provider vulnerability.');
text(page, '70 req/s', 76, 224, 660, 130, 100, true);
text(page, '35 secondes depuis un client isolé', 76, 386, 1120, 60, 34);
text(page, 'Le quota partagé de l’API s’épuise et des paiements sont refusés.\nLa quarantaine filtre la source avant ce quota.\nLe script reste borné au seul hôte privé autorisé.', 76, 488, 1120, 158, 28);

page = slide('Reprise et nouvelle transaction vérifiées',
  'Show the dashboard live. Source: output/evidence/recovery.json; incident ' + incident.id
  + '. The displayed duration is detection-to-recovered, not full outage RTO. '
  + 'Before/after consistency and recovery while attack process still running were checked.');
text(page, `${seconds} s`, 76, 210, 700, 145, 112, true);
text(page, 'entre détection et vérification métier', 76, 378, 1120, 64, 34);
text(page, 'Reprise pendant le flux offensif\nTransaction précédente préservée\nNouveau paiement : ' + proof.transaction_id.slice(0, 8), 76, 488, 1120, 160, 29);

page = slide('Détection ML et garde-fous',
  'Lucas: I am Lucas CHEVALIER, responsible for AI and data. Source: services/supervisor/model.py, '
  + 'output/evidence/calibration.json and recovery.json. Explain small dataset and protected sources. '
  + 'Describe TF-IDF retrieval, LangChain and the local qwen3:0.6b assistant separately from remediation.');
text(page, 'OneClassSVM appris sur le trafic normal observé', 76, 204, 1120, 75, 36, true);
text(page, 'Débit, erreurs, latence et refus d’authentification\nDeux décisions anormales avant déclenchement\nQuarantaine limitée à une source dominante non protégée', 76, 316, 1120, 180, 29);
text(page, 'Le RAG local cite les procédures et reste sans droit d’action.\nL’évaluation doit être étendue au-delà de cette recette.', 76, 548, 1120, 104, 27);

page = slide('Équipe, risques et validation terrain',
  'Jean-christophe: I am Jean-christophe MALINUR, responsible for transformation and governance. '
  + 'Sources: docs/governance.md, docs/team.md, docs/demo-runbook.md. Roles were assigned by request; '
  + 'do not claim individual contributions without their evidence. No regulatory compliance claim.');
const roles = project.members.map(m => `${m.name} : ${m.role}`).join('\n');
text(page, roles, 76, 198, 1120, 240, 28);
text(page, 'Risques EBIOS, PCA/PRA et écarts NIS2/DORA documentés.\nÀ finaliser : essai sur deux PC, confiance TLS, contributions\net vidéo continue de 60 secondes.', 76, 510, 1120, 140, 27);

for (const [index, item] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide: item, format: 'png', scale: 1 });
  await fs.writeFile(path.join(temp, `slide-${index + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
const candidatePath = path.join(temp, 'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const { finalizePresentation } = await import(pathToFileURL(
  path.join(skill, 'container_tools/artifact_tool_utils.mjs'),
).href);
const result = await finalizePresentation({
  workspaceDir: root, candidatePath,
  finalPath: path.join(output, project.delivery_slug + '-Pres' + revision + '.pptx'),
  pythonExecutable: process.env.RUNTIME_PYTHON,
  integrityValidatorPath: path.join(skill, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skill, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-heading-fit'],
  explicitTotalSlideCount: 6,
  requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: 'design', families: ['Arial'] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(temp, 'validation' + revision + '.json'),
});
console.log(JSON.stringify({ finalPath: path.join(output, project.delivery_slug + '-Pres' + revision + '.pptx') }));
