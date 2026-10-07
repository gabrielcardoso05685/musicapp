# MusicApp

Projeto iniciante de um catálogo de músicas feito com Python, Flask, Jinja, HTML, CSS e SQLite. Não reproduz áudio: as músicas são os produtos cadastrados.

## Executar no Windows

Instale Python 3.11 ou superior e execute na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Abra http://127.0.0.1:5000. Clique em **CADASTRAR**, crie sua conta e entre. Cadastre primeiro um artista e depois suas músicas. O banco é criado automaticamente em `instance/musicapp.db` e não é enviado para o GitHub.

## Funcionalidades

- Login sem menu; páginas administrativas com menu superior e submenus popup.
- Usuários: nome, e-mail, celular, nascimento, CPF, nível de acesso, CEP, endereço, número, complemento, cidade e estado, seguindo o modelo fornecido. Senha adicionada para o login.
- Artistas: nome, gênero musical e país.
- Músicas: título, artista, álbum, gênero, duração em segundos, ano e preço.
- Listar, cadastrar, editar, excluir e buscar registros por nome ou título.
- Botões Voltar, Limpar e Salvar; confirmação de exclusão; layout adaptável a telas pequenas.
- Persistência em SQLite, senhas com hash e proteção de formulários contra CSRF.

## Estrutura

`app.py` contém rotas e acesso ao banco. `templates/base.html` é o template comum, com menu opcional. Os demais templates herdam essa base. `static/` contém os estilos e comportamento dos menus.

Rotas: `/login`, `/cadastro`, `/`, `/usuarios`, `/artistas`, `/musicas`. Cada tabela tem também `/<tabela>/cadastrar`, `/<tabela>/<id>/editar` e `/<tabela>/<id>/excluir` (POST). A saída usa `/sair` (POST).

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Limites didáticos

Todos os usuários conectados podem administrar os três cadastros; o nível de acesso é um campo cadastral e não implementa permissões. A recuperação de senha por e-mail não está implementada e a página explica isso. Não há integração de pagamento nem streaming. Use dados fictícios nas demonstrações. O servidor em modo debug é somente para desenvolvimento local. Para outro ambiente, configure `SECRET_KEY` e um servidor apropriado.
