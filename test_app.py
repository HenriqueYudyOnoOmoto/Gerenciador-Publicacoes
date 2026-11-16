import os
import unittest
import tempfile
import sqlite3
from app import app, inicializar_banco, obter_conexao


class TestGerenciadorIdeiasPublicacoes(unittest.TestCase):
    """Testes das operações principais do gerenciador de ideias de publicações."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        app.config['TESTING'] = True
        app.config['DATABASE'] = self.temp_db.name
        app.config['SECRET_KEY'] = 'chave-de-teste'

        inicializar_banco()

        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except PermissionError:
                pass

    def _obter_token_csrf(self):
        """Acessa a rota inicial para gerar a sessão e retorna o token CSRF."""
        self.client.get('/')
        with self.client.session_transaction() as sess:
            return sess.get('csrf_token')

    # 1. Registro válido de ideia
    def test_1_registro_valido(self):
        token = self._obter_token_csrf()
        dados = {
            'titulo': 'Primeira Ideia',
            'conteudo': 'Rascunho de conteúdo para um post futuro.',
            'csrf_token': token
        }
        resposta = self.client.post('/criar', data=dados, follow_redirects=True)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Ideia salva com sucesso!', resposta.get_data(as_text=True))

        # Confirma persistência direta no banco de dados SQLite
        conexao = obter_conexao()
        linha = conexao.execute('SELECT * FROM publicacoes WHERE titulo = ?', ('Primeira Ideia',)).fetchone()
        conexao.close()

        self.assertIsNotNone(linha)
        self.assertEqual(linha['conteudo'], 'Rascunho de conteúdo para um post futuro.')

    # 2. Registro com campos vazios
    def test_2_registro_campos_vazios(self):
        token = self._obter_token_csrf()

        # Tentativa com campos totalmente em branco
        dados_vazios = {
            'titulo': '',
            'conteudo': '',
            'csrf_token': token
        }
        resposta = self.client.post('/criar', data=dados_vazios, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('O título e a descrição são obrigatórios.', resposta.get_data(as_text=True))

        # Tentativa com apenas espaços em branco
        dados_espacos = {
            'titulo': '   ',
            'conteudo': '   ',
            'csrf_token': token
        }
        resposta_espacos = self.client.post('/criar', data=dados_espacos, follow_redirects=True)
        self.assertEqual(resposta_espacos.status_code, 200)
        self.assertIn('O título e a descrição são obrigatórios.', resposta_espacos.get_data(as_text=True))

        # Confirma que nada foi inserido no banco de dados
        conexao = obter_conexao()
        total = conexao.execute('SELECT COUNT(*) as total FROM publicacoes').fetchone()['total']
        conexao.close()
        self.assertEqual(total, 0)

    # 3. Listagem de ideias registradas
    def test_3_listagem_ideias(self):
        # Cenário 1: Banco vazio exibe mensagem informativa
        resposta_vazia = self.client.get('/')
        self.assertEqual(resposta_vazia.status_code, 200)
        self.assertIn('Nenhuma ideia registrada.', resposta_vazia.get_data(as_text=True))

        # Cenário 2: Inserção de dados e listagem correta
        conexao = obter_conexao()
        conexao.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Ideia de Post sobre Python', 'Apresentar 5 dicas de Python para iniciantes.')
        )
        conexao.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Ideia de Vídeo sobre SQLite', 'Explicar vantagens do banco serverless.')
        )
        conexao.commit()
        conexao.close()

        resposta = self.client.get('/')
        self.assertEqual(resposta.status_code, 200)
        conteudo_html = resposta.get_data(as_text=True)

        self.assertIn('Ideia de Post sobre Python', conteudo_html)
        self.assertIn('Apresentar 5 dicas de Python para iniciantes.', conteudo_html)
        self.assertIn('Ideia de Vídeo sobre SQLite', conteudo_html)
        self.assertIn('Explicar vantagens do banco serverless.', conteudo_html)

    # 4. Edição de ideia
    def test_4_edicao_ideia(self):
        # Insere registro inicial
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Ideia Inicial', 'Texto inicial da ideia')
        )
        pub_id = cursor.lastrowid
        conexao.commit()
        conexao.close()

        # Verifica exibição do formulário de edição (GET /editar/<id>)
        resposta_form = self.client.get(f'/editar/{pub_id}')
        self.assertEqual(resposta_form.status_code, 200)
        self.assertIn('Ideia Inicial', resposta_form.get_data(as_text=True))

        # Envia alterações válidas (POST /editar/<id>)
        token = self._obter_token_csrf()
        dados_atualizados = {
            'titulo': 'Ideia Atualizada e Melhorada',
            'conteudo': 'Texto detalhado da ideia após revisão.',
            'csrf_token': token
        }
        resposta_post = self.client.post(f'/editar/{pub_id}', data=dados_atualizados, follow_redirects=True)
        self.assertEqual(resposta_post.status_code, 200)
        self.assertIn('Ideia atualizada com sucesso!', resposta_post.get_data(as_text=True))

        # Confirma alteração no banco de dados
        conexao = obter_conexao()
        registro = conexao.execute('SELECT * FROM publicacoes WHERE id = ?', (pub_id,)).fetchone()
        conexao.close()
        self.assertEqual(registro['titulo'], 'Ideia Atualizada e Melhorada')
        self.assertEqual(registro['conteudo'], 'Texto detalhado da ideia após revisão.')

        # Verifica resposta 404 para ID inexistente
        resposta_inexistente = self.client.get('/editar/9999')
        self.assertEqual(resposta_inexistente.status_code, 404)

    # 5. Exclusão de ideia
    def test_5_exclusao_ideia(self):
        # Insere registro para ser excluído
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Ideia Temporária', 'Será excluída em seguida.')
        )
        pub_id = cursor.lastrowid
        conexao.commit()
        conexao.close()

        token = self._obter_token_csrf()
        resposta = self.client.post(f'/excluir/{pub_id}', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Ideia excluída', resposta.get_data(as_text=True))

        # Confirma que não existe mais no banco de dados
        conexao = obter_conexao()
        registro = conexao.execute('SELECT * FROM publicacoes WHERE id = ?', (pub_id,)).fetchone()
        conexao.close()
        self.assertIsNone(registro)

        # Verifica resposta 404 ao tentar excluir ID que já não existe
        resposta_inexistente = self.client.post('/excluir/9999', data={'csrf_token': token})
        self.assertEqual(resposta_inexistente.status_code, 404)

    # 6. Os dados continuam disponíveis após inicializar o banco novamente
    def test_6_persistencia_apos_nova_inicializacao_do_banco(self):
        # Cadastra uma ideia
        token = self._obter_token_csrf()
        dados = {
            'titulo': 'Ideia Persistente',
            'conteudo': 'Esta ideia deve continuar no banco de dados.',
            'csrf_token': token
        }
        self.client.post('/criar', data=dados)

        # A tabela já existe; inicializar novamente não deve apagar os dados.
        inicializar_banco()
        novo_cliente = app.test_client()

        conexao = obter_conexao()
        registro = conexao.execute(
            'SELECT * FROM publicacoes WHERE titulo = ?',
            ('Ideia Persistente',)
        ).fetchone()
        conexao.close()

        self.assertIsNotNone(registro)
        self.assertEqual(registro['conteudo'], 'Esta ideia deve continuar no banco de dados.')

        resposta = novo_cliente.get('/')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Ideia Persistente', resposta.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
