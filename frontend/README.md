# Frontend BioTraceX

Dashboard React/TypeScript para criar jobs, acompanhar coletas e consultar resultados do NCBI GenBank Extractor.

## Funcionalidades

- upload de CSV com email e nome do dataset;
- lista de jobs e filtro por status;
- página de status com polling a cada 5 segundos;
- indicador de progresso e etapa atual;
- exibição de erros e informações de fila/email;
- resumo de um job concluído;
- espécies sem TaxID e sem sequências;
- download do Excel;
- acionamento do backend de email;
- temas claro e escuro.

## Requisitos

- Node.js 18+;
- npm;
- API FastAPI acessível.

Redis e worker não são requisitos diretos do frontend. A API pode operar com `JOB_BACKEND=inprocess`; se usar `redis`, o backend precisa do Redis e do worker RQ.

## Instalação

```powershell
npm install
```

Crie `.env` quando a API não estiver no endereço padrão:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Desenvolvimento

```powershell
npm run dev
```

Abra `http://localhost:5173`.

A API precisa aceitar essa origem em `CORS_ORIGINS`. O padrão do backend já inclui `http://localhost:5173`.

## Build e lint

```powershell
npm run build
npm run lint
```

O build executa TypeScript e Vite. Para visualizar o build:

```powershell
npm run preview
```

## Docker

O `Dockerfile` usa Node 20 Alpine, executa `npm ci` e inicia o servidor Vite com `--host 0.0.0.0`. Na raiz do projeto, `docker compose up --build` publica a aplicação na porta 5173.

## Estrutura

```text
src/
├── api/jobsApi.ts          cliente e tipos da API
├── components/
│   ├── CreateJob.tsx       criação multipart
│   ├── JobList.tsx         listagem e filtros
│   ├── JobStatus.tsx       polling e ações
│   ├── JobResults.tsx      métricas e falhas
│   ├── BandLadder.tsx      progresso
│   ├── icons.tsx
│   └── ui/                 componentes base
├── hooks/useTheme.ts
├── App.tsx                 rotas e layout
├── main.tsx
└── index.css
```

## Rotas da aplicação

As páginas são definidas em `App.tsx` e cobrem criação, listagem, status e resultados. Após criar um job, a aplicação navega para a tela do identificador retornado pela API.

## Cliente HTTP

`src/api/jobsApi.ts` usa `fetch` e implementa:

- `createJob`;
- `getJobStatus`;
- `downloadJobResult`;
- `sendJobEmail`;
- `listJobs`;
- `getJobSummary`;
- `getFailedSpecies`;
- `triggerDownload`.

Erros não 2xx tentam ler `{ "detail": "..." }` e são convertidos para `Error`. O download usa `Blob` e uma URL temporária do navegador.

Os tipos TypeScript devem ser atualizados sempre que os schemas em `app/schemas/job_schema.py` mudarem.

## Comportamento do status

`JobStatus` pode atualizar automaticamente. O polling para em `completed` ou `failed`; `queue_failed` é exibido como erro, mas deve ser considerado também ao alterar a condição de parada.

Downloads e email ficam disponíveis somente quando o job aparece como concluído. A página de resultados chama `/summary` e `/failed-species`, que também exigem `completed`.

## Email em desenvolvimento

O botão de email chama a API sem enviar um novo destinatário. A API usa o email salvo na criação. Com `EMAIL_BACKEND=console`, a UI recebe sucesso, mas o backend apenas escreve a mensagem no terminal.

## Troubleshooting

### Falha de conexão

1. abra `http://localhost:8000/api/health`;
2. confira `VITE_API_BASE_URL`;
3. confira `CORS_ORIGINS` na API;
4. observe a aba Network do navegador.

### Job não progride

O frontend só exibe o estado persistido. Verifique `job_backend` no health check e, se for `redis`, confirme o worker. No modo `inprocess`, procure erros no terminal da API.

### Resumo/download retorna caminho inválido

O job provavelmente foi gerado em outro ambiente (por exemplo Docker) e o metadata contém caminho absoluto incompatível com o host atual. Reprocesse no mesmo ambiente da API que servirá o arquivo.

### Alterações de CSS não aparecem

Limpe o cache do navegador ou reinicie o Vite. Para problemas de dependência, remova `node_modules` de forma controlada e rode `npm ci`/`npm install` novamente.

Consulte a [documentação principal](../README.md) e a [referência REST](../docs/API_REFERENCE.md).
