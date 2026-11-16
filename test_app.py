import os
import unittest
import tempfile
import sqlite3
from app import app, inicializar_banco, obter_conexao


class TestGerenciadorPublicacoes(unittest.TestCase):
    """Testes das operações principais do gerenciador."""

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

    # 1. Cadastro válido
    def test_1_cadastro_valido(self):
        token = self._obter_token_csrf()
        dados = {
            'titulo': 'Primeira Publicação',
            'conteudo': 'Conteúdo de teste da primeira publicação.',
            'csrf_token': token
        }
        resposta = self.client.post('/criar', data=dados, follow_redirects=True)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Publicação cadastrada com sucesso!', resposta.get_data(as_text=True))

        # Confirma persistência direta no banco de dados SQLite
        conexao = obter_conexao()
        linha = conexao.execute('SELECT * FROM publicacoes WHERE titulo = ?', ('Primeira Publicação',)).fetchone()
        conexao.close()

        self.assertIsNotNone(linha)
        self.assertEqual(linha['conteudo'], 'Conteúdo de teste da primeira publicação.')

    # 2. Cadastro com campos vazios
    def test_2_cadastro_campos_vazios(self):
        token = self._obter_token_csrf()

        # Tentativa com campos totalmente em branco
        dados_vazios = {
            'titulo': '',
            'conteudo': '',
            'csrf_token': token
        }
        resposta = self.client.post('/criar', data=dados_vazios, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('O título e o conteúdo são obrigatórios.', resposta.get_data(as_text=True))

        # Tentativa com apenas espaços em branco
        dados_espacos = {
            'titulo': '   ',
            'conteudo': '   ',
            'csrf_token': token
        }
        resposta_espacos = self.client.post('/criar', data=dados_espacos, follow_redirects=True)
        self.assertEqual(resposta_espacos.status_code, 200)
        self.assertIn('O título e o conteúdo são obrigatórios.', resposta_espacos.get_data(as_text=True))

        # Confirma que nada foi inserido no banco de dados
        conexao = obter_conexao()
        total = conexao.execute('SELECT COUNT(*) as total FROM publicacoes').fetchone()['total']
        conexao.close()
        self.assertEqual(total, 0)

    # 3. Listagem de publicações
    def test_3_listagem_publicacoes(self):
        # Cenário 1: Banco vazio exibe mensagem informativa
        resposta_vazia = self.client.get('/')
        self.assertEqual(resposta_vazia.status_code, 200)
        self.assertIn('Nenhuma publicação cadastrada.', resposta_vazia.get_data(as_text=True))

        # Cenário 2: Inserção de dados e listagem correta
        conexao = obter_conexao()
        conexao.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Aviso de Reunião', 'A reunião do PIT ocorrerá na sexta-feira.')
        )
        conexao.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Dica de Flask', 'Flask é um microframework simples e eficiente.')
        )
        conexao.commit()
        conexao.close()

        resposta = self.client.get('/')
        self.assertEqual(resposta.status_code, 200)
        conteudo_html = resposta.get_data(as_text=True)

        self.assertIn('Aviso de Reunião', conteudo_html)
        self.assertIn('A reunião do PIT ocorrerá na sexta-feira.', conteudo_html)
        self.assertIn('Dica de Flask', conteudo_html)
        self.assertIn('Flask é um microframework simples e eficiente.', conteudo_html)

    # 4. Edição de publicação
    def test_4_edicao_publicacao(self):
        # Insere registro inicial
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Título Antigo', 'Conteúdo Antigo')
        )
        pub_id = cursor.lastrowid
        conexao.commit()
        conexao.close()

        # Verifica exibição do formulário de edição (GET /editar/<id>)
        resposta_form = self.client.get(f'/editar/{pub_id}')
        self.assertEqual(resposta_form.status_code, 200)
        self.assertIn('Título Antigo', resposta_form.get_data(as_text=True))

        # Envia alterações válidas (POST /editar/<id>)
        token = self._obter_token_csrf()
        dados_atualizados = {
            'titulo': 'Título Novo e Modificado',
            'conteudo': 'Conteúdo totalmente atualizado.',
            'csrf_token': token
        }
        resposta_post = self.client.post(f'/editar/{pub_id}', data=dados_atualizados, follow_redirects=True)
        self.assertEqual(resposta_post.status_code, 200)
        self.assertIn('Publicação atualizada com sucesso!', resposta_post.get_data(as_text=True))

        # Confirma alteração no banco de dados
        conexao = obter_conexao()
        registro = conexao.execute('SELECT * FROM publicacoes WHERE id = ?', (pub_id,)).fetchone()
        conexao.close()
        self.assertEqual(registro['titulo'], 'Título Novo e Modificado')
        self.assertEqual(registro['conteudo'], 'Conteúdo totalmente atualizado.')

        # Verifica resposta 404 para ID inexistente
        resposta_inexistente = self.client.get('/editar/9999')
        self.assertEqual(resposta_inexistente.status_code, 404)

    # 5. Exclusão de publicação
    def test_5_exclusao_publicacao(self):
        # Insere registro para ser excluído
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(
            'INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)',
            ('Publicação Temporária', 'Será excluída em seguida.')
        )
        pub_id = cursor.lastrowid
        conexao.commit()
        conexao.close()

        token = self._obter_token_csrf()
        resposta = self.client.post(f'/excluir/{pub_id}', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Publicação excluída', resposta.get_data(as_text=True))

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
        # Cadastra uma publicação
        token = self._obter_token_csrf()
        dados = {
            'titulo': 'Publicação Persistente',
            'conteudo': 'Estes dados devem continuar no banco.',
            'csrf_token': token
        }
        self.client.post('/criar', data=dados)

        # A tabela já existe; inicializar novamente não deve apagar os dados.
        inicializar_banco()
        novo_cliente = app.test_client()

        conexao = obter_conexao()
        registro = conexao.execute(
            'SELECT * FROM publicacoes WHERE titulo = ?',
            ('Publicação Persistente',)
        ).fetchone()
        conexao.close()

        self.assertIsNotNone(registro)
        self.assertEqual(registro['conteudo'], 'Estes dados devem continuar no banco.')

        resposta = novo_cliente.get('/')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Publicação Persistente', resposta.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
