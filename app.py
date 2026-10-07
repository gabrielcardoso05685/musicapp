"""Aplicação didática: Flask, templates Jinja e banco SQLite."""
import os
import secrets
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

USER_FIELDS = [('nome', 'Nome', 'text', 6), ('email', 'Email', 'email', 6), ('celular', 'Celular', 'tel', 3), ('nascimento', 'Data de Nascimento', 'date', 3), ('cpf', 'CPF', 'text', 3), ('nivel', 'Nível de Acesso', 'select', 3), ('cep', 'CEP', 'text', 3), ('endereco', 'Endereço', 'text', 7), ('numero', 'Número', 'text', 2), ('complemento', 'Complemento', 'text', 4), ('cidade', 'Cidade', 'text', 4), ('estado', 'Estado', 'select', 4), ('senha', 'Senha', 'password', 12)]
ENTITIES = {
    'usuarios': {'title': 'Usuários', 'fields': USER_FIELDS, 'columns': [('nome', 'Nome'), ('email', 'Email'), ('celular', 'Celular'), ('nivel', 'Nível')]},
    'artistas': {'title': 'Artistas', 'fields': [('nome', 'Nome', 'text', 6), ('genero', 'Gênero musical', 'text', 6), ('pais', 'País', 'text', 6)], 'columns': [('nome', 'Nome'), ('genero', 'Gênero'), ('pais', 'País')]},
    'musicas': {'title': 'Músicas', 'fields': [('titulo', 'Título', 'text', 6), ('artista_id', 'Artista', 'select', 6), ('album', 'Álbum', 'text', 6), ('genero', 'Gênero musical', 'text', 6), ('duracao', 'Duração (segundos)', 'number', 4), ('ano', 'Ano de lançamento', 'number', 4), ('preco', 'Preço (R$)', 'number', 4)], 'columns': [('titulo', 'Título'), ('artista', 'Artista'), ('album', 'Álbum'), ('preco', 'Preço (R$)')]},
}
STATES = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), DATABASE=str(Path(app.instance_path) / 'musicapp.db'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def db():
        connection = sqlite3.connect(app.config['DATABASE'])
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db() as connection:
        connection.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            celular TEXT, nascimento TEXT, cpf TEXT, nivel TEXT NOT NULL,
            cep TEXT, endereco TEXT, numero TEXT, complemento TEXT, cidade TEXT,
            estado TEXT, senha TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS artistas (
            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, genero TEXT, pais TEXT);
        CREATE TABLE IF NOT EXISTS musicas (
            id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, artista_id INTEGER NOT NULL
            REFERENCES artistas(id), album TEXT, genero TEXT,
            duracao INTEGER NOT NULL CHECK(duracao > 0), ano INTEGER,
            preco REAL NOT NULL CHECK(preco >= 0));
        ''')

    def protected(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    @app.before_request
    def csrf_check():
        if request.method == 'POST' and request.form.get('csrf_token') != session.get('csrf_token'):
            abort(400, 'Formulário expirado. Atualize a página.')
        session.setdefault('csrf_token', secrets.token_hex(24))

    @app.context_processor
    def context():
        return dict(entities=ENTITIES)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            with db() as connection:
                user = connection.execute('SELECT * FROM usuarios WHERE email = ?', (request.form.get('email', '').strip().lower(),)).fetchone()
            if user and check_password_hash(user['senha'], request.form.get('senha', '')):
                session['user_id'] = user['id']
                return redirect(url_for('home'))
            flash('E-mail ou senha inválidos.', 'error')
        return render_template('login.html', no_menu=True)

    @app.post('/sair')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @protected
    def home():
        with db() as connection:
            counts = {key: connection.execute(f'SELECT COUNT(*) FROM {key}').fetchone()[0] for key in ENTITIES}
        return render_template('home.html', counts=counts)

    @app.get('/<entity>')
    @protected
    def listing(entity):
        if entity not in ENTITIES:
            abort(404)
        query = request.args.get('q', '').strip()
        field = 'titulo' if entity == 'musicas' else 'nome'
        sql = 'SELECT m.*, a.nome AS artista FROM musicas m JOIN artistas a ON a.id=m.artista_id' if entity == 'musicas' else f'SELECT * FROM {entity}'
        with db() as connection:
            rows = connection.execute(sql + f' WHERE {field} LIKE ? ORDER BY id DESC', ('%' + query + '%',)).fetchall()
        return render_template('list.html', entity=entity, config=ENTITIES[entity], rows=rows, query=query)

    @app.route('/cadastro', methods=['GET', 'POST'])
    def register():
        return form('usuarios', public=True)

    @app.route('/<entity>/cadastrar', methods=['GET', 'POST'])
    @protected
    def add(entity):
        return form(entity)

    @app.route('/<entity>/<int:record_id>/editar', methods=['GET', 'POST'])
    @protected
    def edit(entity, record_id):
        return form(entity, record_id)

    def form(entity, record_id=None, public=False):
        if entity not in ENTITIES:
            abort(404)
        config = ENTITIES[entity]
        with db() as connection:
            row = connection.execute(f'SELECT * FROM {entity} WHERE id=?', (record_id,)).fetchone() if record_id else None
            artists = connection.execute('SELECT id, nome FROM artistas ORDER BY nome').fetchall()
        if record_id and row is None:
            abort(404)
        values = dict(row) if row else {}
        if request.method == 'POST':
            values = {name: request.form.get(name, '').strip() for name, *_ in config['fields']}
            try:
                if not values.get('nome', values.get('titulo')):
                    raise ValueError('Preencha o nome ou título.')
                if entity == 'usuarios':
                    values['email'] = values['email'].lower()
                    if '@' not in values['email'] or not values['email'].split('@')[-1]:
                        raise ValueError('Informe um e-mail válido.')
                    if public:
                        values['nivel'] = 'Usuário'
                    if values['nivel'] not in ['Usuário', 'Administrador'] or values['estado'] not in STATES + ['']:
                        raise ValueError('Selecione um nível de acesso e estado válidos.')
                    if values['senha']:
                        if len(values['senha']) < 6:
                            raise ValueError('A senha precisa ter pelo menos 6 caracteres.')
                        values['senha'] = generate_password_hash(values['senha'])
                    elif record_id:
                        values.pop('senha')
                    else:
                        raise ValueError('Informe uma senha.')
                if entity == 'musicas':
                    values['duracao'] = int(values['duracao'])
                    values['ano'] = int(values['ano']) if values['ano'] else None
                    values['preco'] = float(values['preco'].replace(',', '.'))
                    values['artista_id'] = int(values['artista_id'])
                    if values['duracao'] <= 0 or not 0 <= values['preco'] < 1000000 or (values['ano'] is not None and not 1000 <= values['ano'] <= 9999):
                        raise ValueError('Verifique a duração, o ano e o preço.')
                with db() as connection:
                    if record_id:
                        connection.execute(f'UPDATE {entity} SET ' + ', '.join(f'{key}=?' for key in values) + ' WHERE id=?', [*values.values(), record_id])
                    else:
                        connection.execute(f'INSERT INTO {entity} (' + ', '.join(values) + ') VALUES (' + ', '.join('?' for _ in values) + ')', list(values.values()))
                flash('Cadastro salvo com sucesso.', 'success')
                return redirect(url_for('login') if public else url_for('listing', entity=entity))
            except (ValueError, sqlite3.IntegrityError):
                flash('Não foi possível salvar. Verifique os campos, o e-mail duplicado e o artista selecionado. Senhas devem ter ao menos 6 caracteres.', 'error')
                values = request.form.to_dict()
        return render_template('form.html', entity=entity, config=config, values=values, artists=artists, states=STATES, editing=bool(record_id), public=public, no_menu=public)

    @app.post('/<entity>/<int:record_id>/excluir')
    @protected
    def delete(entity, record_id):
        if entity not in ENTITIES:
            abort(404)
        if entity == 'usuarios' and record_id == session['user_id']:
            flash('Você não pode excluir o usuário da sessão atual.', 'error')
        else:
            try:
                with db() as connection:
                    connection.execute(f'DELETE FROM {entity} WHERE id=?', (record_id,))
                flash('Registro excluído.', 'success')
            except sqlite3.IntegrityError:
                flash('Exclua primeiro as músicas vinculadas a este artista.', 'error')
        return redirect(url_for('listing', entity=entity))

    @app.get('/recuperar-senha')
    def recover():
        return render_template('recover.html', no_menu=True)

    return app


if __name__ == '__main__':
    create_app().run(debug=True)
