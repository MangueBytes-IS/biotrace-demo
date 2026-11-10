# Subindo a versão demo (gratuito)

Arquitetura:

- **API (Flask + coleta):** VM Linux da Oracle Cloud (Always Free), com Docker, Caddy (HTTPS automático) e volume persistente.
- **Frontend:** site estático no Netlify.
- **Domínio:** subdomínio grátis no DuckDNS.

## 0. Cuidado com o cartão

A Oracle pede cartão para verificar a conta. Para não ser cobrado:

1. Crie a conta e **não faça upgrade** para "Pay As You Go".
2. Crie a VM só com a forma **VM.Standard.A1.Flex** (ARM), 1 OCPU e 6 GB de RAM. É a forma gratuita.
3. Em **Billing > Budgets**, crie um orçamento de **R$ 1** com alerta por email.
4. Não crie Load Balancer, Object Storage extra nem bancos pagos.

Se preferir não usar cartão, a alternativa é o Render (plano gratuito), mas ele apaga o disco e encerra o serviço sem tráfego. Coletas longas e dados se perdem. Não recomendo para esta versão.

## 1. Domínio (DuckDNS)

1. Entre em duckdns.org com uma conta gratuita.
2. Crie um subdomínio, por exemplo `biotracex`. O endereço será `biotracex.duckdns.org`.
3. Coloque o IP público da VM no campo "current ip" e salve.

## 2. VM na Oracle

1. Crie a instância: imagem **Ubuntu 22.04**, forma A1.Flex (1 OCPU, 6 GB), com IP público.
2. Baixe a chave SSH na criação. Conecte com `ssh -i chave.key ubuntu@IP_DA_VM`.
3. Libere as portas 80 e 443 em **Networking > Security List** (regra de entrada TCP).
4. Dentro da VM, libere o firewall do sistema:
   ```bash
   sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save   # ou: sudo apt install -y iptables-persistent
   ```
5. Instale o Docker:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER   # depois saia e entre de novo no SSH
   ```

### 2.1 Endurecimento da VM (obrigatório)

Gratuito não quer dizer exposto. Depois de conectar pela primeira vez:

1. **Só login por chave SSH.** Em `/etc/ssh/sshd_config`, defina `PasswordAuthentication no` e `PermitRootLogin no`. Depois: `sudo systemctl restart ssh`. Antes de fechar a sessão atual, abra outra e confirme que entra com a chave.
2. **Atualizações de segurança automáticas:**
   ```bash
   sudo apt update && sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```
3. **Só três portas abertas:** 22 (SSH), 80 e 443. O compose não publica a porta da API, então ela só é acessível pelo Caddy.
4. **Permissões do arquivo de segredos:** `chmod 600 ~/biotracex/deploy/.env.prod`.
5. **Grupo `docker` equivale a root.** Só o usuário `ubuntu` deve estar nele.
6. **Disco:** as análises ficam no volume. Acompanhe com `df -h` e, se for preciso, exclua contas antigas com `delete_user.py`.
7. **Não instale nada extra** na VM. Quanto menos software, menos superfície de ataque.

## 3. Código e configuração

```bash
git clone https://github.com/MangueBytes-IS/biotrace-demo.git biotracex
cd biotracex/deploy
cp .env.prod.example .env.prod   # crie este arquivo a partir do exemplo abaixo
```

Conteúdo de `deploy/.env.prod` (troque os valores):

```
DOMAIN=biotracex.duckdns.org
NCBI_EMAIL=seu-email-real@exemplo.com
CORS_ORIGINS=https://SEU-SITE.netlify.app
```

`CORS_ORIGINS` é o endereço do frontend depois do passo 5. Pode deixar o valor provisório e ajustar depois.

## 4. Subir a API

```bash
cd ~/biotracex/deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml ps
curl -I https://biotracex.duckdns.org/api/health   # deve responder 200
```

O Caddy emite o certificado sozinho na primeira requisição. Se não funcionar, confira se o DuckDNS já aponta para o IP certo e se as portas 80 e 443 estão abertas.

Backup diário (opcional, recomendado):

```bash
chmod +x ~/biotracex/deploy/backup.sh
(crontab -l 2>/dev/null; echo "0 3 * * * $HOME/biotracex/deploy/backup.sh") | crontab -
```

## 5. Frontend no Netlify

1. Entre em netlify.com com a conta gratuita e clique em **Add new site > Import an existing project**.
2. Escolha o repositório e a branch `demo`.
3. Configure:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `dist`
4. Em **Environment variables**, adicione `VITE_API_URL=https://biotracex.duckdns.org`.
5. Faça o deploy. O Netlify dá um endereço `https://nome.netlify.app`.
6. Volte à VM, coloque esse endereço em `CORS_ORIGINS` no `.env.prod` e reinicie a API:
   ```bash
   cd ~/biotracex/deploy
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

Como o Vite grava `VITE_API_URL` no build, se o domínio mudar é preciso fazer um novo deploy no Netlify.

## 6. Checklist antes de divulgar

- [ ] `https://biotracex.duckdns.org/api/health` responde 200
- [ ] Criar conta, sair e entrar de novo funciona
- [ ] Senha errada 5 vezes bloqueia a entrada
- [ ] Envio de CSV com 21 espécies é recusado
- [ ] Segunda coleta enquanto a primeira roda é recusada
- [ ] O link "excluir conta" do aviso abre o email de contato

## 7. Operação

- **Excluir uma conta** (pedido por email):
  ```bash
  docker compose -f docker-compose.prod.yml exec backend python delete_user.py email@exemplo.com
  ```
  Os backups antigos continuam com os dados até expirarem (7 dias pelo `backup.sh`).
- **Ver logs:** `docker compose -f docker-compose.prod.yml logs -f backend`
- **Atualizar a versão:** `git pull && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
- **Reinício da VM:** os containers voltam sozinhos (`restart: unless-stopped`). Uma coleta que estava rodando vira falha e o usuário precisa reenviar o CSV.

## Limites conhecidos desta versão

- Login com senha, mas sem confirmação de email: quem cadastra um email alheio não recebe aviso.
- Bloqueio de tentativas é por email, não por IP.
- A VM gratuita pode ser recuperada pela Oracle se ficar muito ociosa por muito tempo. Faça backup antes de qualquer mudança grande.
