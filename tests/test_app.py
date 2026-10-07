import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class MusicAppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp.name) / 'test.db')
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'DATABASE': self.database})
        self.client = self.app.test_client()
        self.client.get('/login')

    def tearDown(self):
        self.temp.cleanup()

    def post(self, path, data=None):
        with self.client.session_transaction() as session:
            token = session['csrf_token']
        return self.client.post(path, data={**(data or {}), 'csrf_token': token}, follow_redirects=True)

    def login(self):
        self.post('/cadastro', {'nome': 'Teste', 'email': 'teste@example.com', 'senha': 'senha123', 'nivel': 'Administrador'})
        return self.post('/login', {'email': 'teste@example.com', 'senha': 'senha123'})

    def test_login_and_public_registration(self):
        self.assertEqual(self.client.get('/usuarios').status_code, 302)
        self.assertNotIn(b'Menu principal', self.client.get('/login').data)
        self.assertIn(b'Bem-vindo', self.login().data)
        with closing(sqlite3.connect(self.database)) as connection:
            level, password = connection.execute('SELECT nivel, senha FROM usuarios').fetchone()
        self.assertEqual(level, 'Usuário')
        self.assertNotEqual(password, 'senha123')
        self.assertIn(b'Menu principal', self.client.get('/usuarios').data)
        self.assertIn(b'Login', self.post('/sair').data)
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_catalog_crud_search_and_relations(self):
        self.login()
        for entity in ['usuarios', 'artistas', 'musicas']:
            self.assertEqual(self.client.get(f'/{entity}').status_code, 200)
            self.assertEqual(self.client.get(f'/{entity}/cadastrar').status_code, 200)
        self.post('/artistas/cadastrar', {'nome': 'Artista Teste', 'genero': 'Pop', 'pais': 'Brasil'})
        music = {'titulo': 'Canção Teste', 'artista_id': '1', 'album': 'Disco', 'genero': 'Pop', 'duracao': '180', 'ano': '2026', 'preco': '9.90'}
        self.assertIn('Canção Teste', self.post('/musicas/cadastrar', music).text)
        self.assertIn('Artista Teste', self.client.get('/musicas').text)
        self.assertNotIn('Canção Teste', self.client.get('/musicas?q=inexistente').text)
        self.assertIn('vinculadas', self.post('/artistas/1/excluir').text)
        self.assertEqual(self.client.get('/musicas/1/editar').status_code, 200)
        self.assertIn('Nova Música', self.post('/musicas/1/editar', {**music, 'titulo': 'Nova Música'}).text)
        self.post('/musicas/1/excluir')
        self.post('/artistas/1/excluir')
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM musicas').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM artistas').fetchone()[0], 0)

    def test_validation_csrf_duplicate_and_current_user(self):
        self.login()
        self.assertEqual(self.client.post('/artistas/cadastrar', data={'nome': 'Sem token'}).status_code, 400)
        response = self.post('/usuarios/cadastrar', {'nome': 'Duplicado', 'email': 'teste@example.com', 'senha': 'senha123', 'nivel': 'Usuário'})
        self.assertIn('Não foi possível', response.text)
        self.assertIn('sessão atual', self.post('/usuarios/1/excluir').text)
        self.post('/artistas/cadastrar', {'nome': 'Artista'})
        self.assertIn('Não foi possível', self.post('/musicas/cadastrar', {'titulo': 'Inválida', 'artista_id': '1', 'duracao': '-1', 'preco': '1'}).text)
        self.assertEqual(self.client.get('/desconhecida').status_code, 404)
        self.assertEqual(self.client.get('/usuarios/999/editar').status_code, 404)

    def test_user_edit_and_delete(self):
        self.login()
        user = {'nome': 'Segundo', 'email': 'segundo@example.com', 'senha': 'senha123', 'nivel': 'Usuário'}
        self.post('/usuarios/cadastrar', user)
        self.assertEqual(self.client.get('/usuarios/2/editar').status_code, 200)
        self.post('/usuarios/2/editar', {**user, 'nome': 'Alterado', 'senha': ''})
        self.assertIn('Alterado', self.client.get('/usuarios').text)
        self.post('/usuarios/2/excluir')
        self.assertNotIn('segundo@example.com', self.client.get('/usuarios').text)


if __name__ == '__main__':
    unittest.main()
