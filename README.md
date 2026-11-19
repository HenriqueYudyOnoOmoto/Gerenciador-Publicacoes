# Gerenciador de Ideias para Publicações

Trabalho da PIT II. É um site simples para guardar ideias de publicações (posts, vídeos, etc).
Dá para cadastrar, ver, editar, excluir e marcar a ideia como já postada.

## Tecnologias

- Python e Flask
- SQLite
- HTML, CSS e um pouco de JavaScript

## Como rodar (Windows)

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Depois, abra <http://127.0.0.1:5000/> no navegador.
O arquivo `publicacoes.db` é criado sozinho na primeira vez.

## Arquivos

- `app.py` - rotas e banco de dados
- `templates/index.html` - página principal (cadastro e lista)
- `templates/editar.html` - página de editar
- `static/style.css` - estilo
