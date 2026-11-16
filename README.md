# Gerenciador de Ideias para Publicações

Projeto acadêmico de PIT II. O sistema é um gerenciador de ideias para publicações futuras, permitindo que o usuário registre, visualize, edite e exclua ideias de conteúdos que pretende produzir ou publicar posteriormente.

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

Os testes usam um banco temporário. Eles verificam registro de ideias, validação de campos vazios, listagem de ideias registradas, edição, exclusão e persistência após reinicialização da estrutura do banco.

## Arquivos principais

- `app.py`: rotas, validações e acesso ao SQLite.
- `templates/index.html`: registro e listagem de ideias.
- `templates/editar.html`: formulário de edição de ideia.
- `static/style.css`: estilos da página.
- `test_app.py`: testes automatizados.

## Segurança e limites

As consultas utilizam parâmetros no SQLite para proteção contra injeção de SQL. Formulários que alteram dados utilizam token CSRF, e a exclusão só aceita requisições `POST`.

O sistema guarda apenas texto e não possui agendamento, calendário, categorias, publicação automática ou integração com redes sociais.
