import os
import unittest
import tempfile
import sqlite3
from app import app, inicializar_banco, obter_conexao


class TestGerenciadorIdeiasPublicacoes(unittest.TestCase):
    """Testes das operações principais do gerenciador de ideias para publicações."""

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

    # 7. Marcar e desmarcar ideia como postada
    def test_7_marcar_e_desmarcar_postada(self):
        token = self._obter_token_csrf()
        dados = {
            'titulo': 'Ideia para Instagram',
            'conteudo': 'Roteiro pronto para publicação.',
            'csrf_token': token
        }
        self.client.post('/criar', data=dados)

        conexao = obter_conexao()
        pub_id = conexao.execute('SELECT id FROM publicacoes WHERE titulo = ?', ('Ideia para Instagram',)).fetchone()['id']
        conexao.close()

        # 1. Marcar como postada
        res_marcar = self.client.post(f'/alternar-postada/{pub_id}', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(res_marcar.status_code, 200)
        html_marcada = res_marcar.get_data(as_text=True)
        self.assertIn('Ideia marcada como postada!', html_marcada)
        self.assertIn('ideia-postada', html_marcada)
        self.assertIn('Desmarcar', html_marcada)

        # Confirma estado 1 no banco SQLite
        conexao = obter_conexao()
        status = conexao.execute('SELECT postada FROM publicacoes WHERE id = ?', (pub_id,)).fetchone()['postada']
        conexao.close()
        self.assertEqual(status, 1)

        # 2. Desmarcar
        res_desmarcar = self.client.post(f'/alternar-postada/{pub_id}', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(res_desmarcar.status_code, 200)
        html_desmarcada = res_desmarcar.get_data(as_text=True)
        self.assertIn('Ideia desmarcada!', html_desmarcada)
        self.assertIn('Marcar como postada', html_desmarcada)

        # Confirma estado 0 no banco SQLite
        conexao = obter_conexao()
        status_novo = conexao.execute('SELECT postada FROM publicacoes WHERE id = ?', (pub_id,)).fetchone()['postada']
        conexao.close()
        self.assertEqual(status_novo, 0)

    # 8. Ordenação: ideias pendentes primeiro e postadas ao final
    def test_8_ordenacao_pendentes_primeiro_e_postadas_ao_final(self):
        token = self._obter_token_csrf()
        # Cadastra Ideia A e Ideia B
        self.client.post('/criar', data={'titulo': 'Ideia A', 'conteudo': 'Conteudo A', 'csrf_token': token})
        self.client.post('/criar', data={'titulo': 'Ideia B', 'conteudo': 'Conteudo B', 'csrf_token': token})

        conexao = obter_conexao()
        id_b = conexao.execute('SELECT id FROM publicacoes WHERE titulo = ?', ('Ideia B',)).fetchone()['id']
        conexao.close()

        # Marca Ideia B como postada
        self.client.post(f'/alternar-postada/{id_b}', data={'csrf_token': token})

        # Cadastra Ideia C (pendente)
        self.client.post('/criar', data={'titulo': 'Ideia C', 'conteudo': 'Conteudo C', 'csrf_token': token})

        # Na listagem, Ideia C e Ideia A (pendentes) devem vir antes de Ideia B (postada)
        resposta = self.client.get('/')
        html = resposta.get_data(as_text=True)

        pos_c = html.find('Ideia C')
        pos_a = html.find('Ideia A')
        pos_b = html.find('Ideia B')

        self.assertTrue(pos_c < pos_b, 'Ideia pendente C deve vir antes da postada B')
        self.assertTrue(pos_a < pos_b, 'Ideia pendente A deve vir antes da postada B')

    # 9. Alternar postada com ID inexistente retorna 404
    def test_9_alternar_postada_inexistente_404(self):
        token = self._obter_token_csrf()
        resposta = self.client.post('/alternar-postada/9999', data={'csrf_token': token})
        self.assertEqual(resposta.status_code, 404)


if __name__ == '__main__':
    unittest.main()
