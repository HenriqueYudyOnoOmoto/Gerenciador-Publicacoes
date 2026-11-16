# Gerenciador de Publicações

Projeto acadêmico de PIT II. O sistema permite cadastrar, listar, editar e excluir publicações de texto.

## Tecnologias

- Python 3.12
- Flask
- SQLite
- HTML e CSS
- `unittest` para os testes

## Executar no Windows

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000/> no navegador. O banco `publicacoes.db` e a tabela são criados automaticamente.

## Testar

```powershell
python -m unittest test_app.py -v
```

Os testes usam um banco temporário. Eles verificam cadastro, validação de campos vazios, listagem, edição, exclusão e se os dados permanecem após inicializar a estrutura do banco novamente.

## Arquivos principais

- `app.py`: rotas, validações e acesso ao SQLite.
- `templates/index.html`: cadastro e listagem.
- `templates/editar.html`: formulário de edição.
- `static/style.css`: estilos da página.
- `test_app.py`: testes automatizados.

## Segurança e limites

As consultas usam parâmetros do SQLite. Formulários que alteram dados usam token CSRF, e a exclusão só aceita `POST`. A aplicação não tem login e foi preparada para uso local. Antes de publicá-la na internet, configure uma `SECRET_KEY` estável e use um servidor de produção; não use o servidor de desenvolvimento do Flask como hospedagem.

O sistema guarda apenas texto e não tem pesquisa, paginação ou controle de usuários.
