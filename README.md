# BioTraceX — versão demo

Coleta de dados do GenBank/NCBI a partir de uma lista de espécies. Você envia um CSV com um nome científico por linha e recebe um relatório em Excel com sequências, genes, metadados e gráficos.

## Limites da versão demo

- Até 20 espécies por análise.
- Até 3 análises por dia por conta.
- Uma coleta por vez no servidor.
- Cada espécie leva cerca de 3 minutos para ser consultada.

## Rodando localmente

Com Docker:

```bash
docker build -t biotracex-demo .
docker run --rm -p 127.0.0.1:7860:7860 -e NCBI_EMAIL=seu-email@exemplo.com biotracex-demo
```

Depois abra `http://127.0.0.1:7860`.

`NCBI_EMAIL` é enviado ao NCBI para identificar as consultas, como o NCBI exige.

## Estrutura

- `frontend/`: interface em React + Vite.
- `backend/`: API em Flask (login, análises, download).
- `ncbi_collector.py`: coletor que consulta o NCBI e gera o Excel.
- `Dockerfile`: imagem única que compila o frontend e serve tudo pelo Flask.
- `deploy/`: guia e arquivos para subir em uma VM Linux com HTTPS.

## Privacidade

Esta é uma versão demo. Não use senhas reais nem dados pessoais sensíveis. Para excluir sua conta e seus dados, escreva para manguebytes@gmail.com.

## Licença

Veja [LICENSE](LICENSE).
