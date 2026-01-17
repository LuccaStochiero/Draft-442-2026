# Guia de Deploy (Implantação)

Este guia descreve como colocar seu app no ar usando **GitHub**, **Render** (Backend) e **Vercel** (Frontend).

## 1. Preparação do GitHub
Você precisa colocar seu código em um repositório Git.

1.  Abra o terminal na pasta raiz do projeto (`.../Playbook/442`).
2.  Inicialize o git e suba o código:
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    # Crie um repositório no GitHub (https://github.com/new)
    # Siga as instruções para 'push an existing repository', ex:
    git branch -M main
    git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
    git push -u origin main
    ```

## 2. Deploy do Backend (Render)
O backend Python precisa estar no ar primeiro.

1.  Crie uma conta em [Render.com](https://render.com).
2.  Clique em **New +** -> **Web Service**.
3.  Conecte seu repositório do GitHub.
4.  Configure:
    *   **Name**: `fantasy-draft-backend` (exemplo)
    *   **Root Directory**: `web-app/backend`
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5.  Clique em **Create Web Service**.
6.  Aguarde o deploy finalizar. Copie a URL do serviço (ex: `https://fantasy-backend.onrender.com`).

## 3. Deploy do Frontend (Vercel)
Agora vamos subir o site (frontend).

1.  Crie uma conta em [Vercel.com](https://vercel.com).
2.  Clique em **Add New ...** -> **Project**.
3.  Importe seu repositório do GitHub.
4.  Configure:
    *   **Root Directory**: Clique em `Edit` e selecione `web-app/frontend`.
    *   **Framework Preset**: Next.js (deve detectar automático).
    *   **Environment Variables**:
        *   Nome: `NEXT_PUBLIC_API_URL`
        *   Valor: A URL do seu backend no Render (ex: `https://fantasy-backend.onrender.com/api`) **IMPORTANTE: Adicione `/api` no final se sua rota base for essa, ou deixe sem se o backend tratar.**
5.  Clique em **Deploy**.

## 4. Teste
Acesse a URL gerada pela Vercel. Seu app deve estar funcionando e conectado ao backend!

## Notas Importantes
*   **Dados**: O arquivo `Players.csv` atualizado que estamos gerando agora será enviado junto com o código para o Render. Se você rodar o scraper novamente localmente, precisará fazer um novo `git add .`, `git commit` e `git push` para atualizar os dados no servidor.
