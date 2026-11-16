import os
import secrets
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# O banco fica ao lado deste arquivo. Os testes trocam esse caminho por um temporário.
CAMINHO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "publicacoes.db")
app.config["DATABASE"] = CAMINHO_BANCO


def obter_conexao():
    conexao = sqlite3.connect(app.config.get("DATABASE", CAMINHO_BANCO))
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    conexao = obter_conexao()
    conexao.execute(
        """CREATE TABLE IF NOT EXISTS publicacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL
        )"""
    )
    conexao.commit()
    conexao.close()


def obter_token_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


@app.context_processor
def injetar_csrf():
    return {"csrf_token": obter_token_csrf()}


@app.before_request
def verificar_csrf():
    # Requisições que alteram dados precisam do token enviado pelo formulário.
    if request.method == "POST" and app.config.get("WTF_CSRF_ENABLED") is not False:
        token_enviado = request.form.get("csrf_token")
        if not token_enviado or token_enviado != session.get("csrf_token"):
            abort(400, description="Requisição inválida: token de segurança ausente ou incorreto.")


@app.route("/")
def index():
    conexao = obter_conexao()
    publicacoes = conexao.execute(
        "SELECT id, titulo, conteudo FROM publicacoes ORDER BY id DESC"
    ).fetchall()
    conexao.close()
    return render_template("index.html", publicacoes=publicacoes)


@app.route("/criar", methods=["POST"])
def criar():
    titulo = request.form.get("titulo", "").strip()
    conteudo = request.form.get("conteudo", "").strip()

    if not titulo or not conteudo:
        flash("O título e o conteúdo são obrigatórios.", "erro")
        return redirect(url_for("index"))
    if len(titulo) > 100:
        flash("O título não pode exceder 100 caracteres.", "erro")
        return redirect(url_for("index"))
    if len(conteudo) > 2000:
        flash("O conteúdo não pode exceder 2000 caracteres.", "erro")
        return redirect(url_for("index"))

    conexao = obter_conexao()
    conexao.execute(
        "INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)",
        (titulo, conteudo),
    )
    conexao.commit()
    conexao.close()
    flash("Publicação cadastrada com sucesso!", "sucesso")
    return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET"])
def editar(id):
    conexao = obter_conexao()
    publicacao = conexao.execute(
        "SELECT id, titulo, conteudo FROM publicacoes WHERE id = ?", (id,)
    ).fetchone()
    conexao.close()

    if publicacao is None:
        abort(404, description="Publicação não encontrada.")
    return render_template("editar.html", publicacao=publicacao)


@app.route("/editar/<int:id>", methods=["POST"])
def editar_salvar(id):
    conexao = obter_conexao()
    publicacao = conexao.execute(
        "SELECT id FROM publicacoes WHERE id = ?", (id,)
    ).fetchone()
    if publicacao is None:
        conexao.close()
        abort(404, description="Publicação não encontrada.")

    titulo = request.form.get("titulo", "").strip()
    conteudo = request.form.get("conteudo", "").strip()
    if not titulo or not conteudo:
        conexao.close()
        flash("O título e o conteúdo são obrigatórios.", "erro")
        return redirect(url_for("editar", id=id))
    if len(titulo) > 100:
        conexao.close()
        flash("O título não pode exceder 100 caracteres.", "erro")
        return redirect(url_for("editar", id=id))
    if len(conteudo) > 2000:
        conexao.close()
        flash("O conteúdo não pode exceder 2000 caracteres.", "erro")
        return redirect(url_for("editar", id=id))

    conexao.execute(
        "UPDATE publicacoes SET titulo = ?, conteudo = ? WHERE id = ?",
        (titulo, conteudo, id),
    )
    conexao.commit()
    conexao.close()
    flash("Publicação atualizada com sucesso!", "sucesso")
    return redirect(url_for("index"))


@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    conexao = obter_conexao()
    publicacao = conexao.execute(
        "SELECT id FROM publicacoes WHERE id = ?", (id,)
    ).fetchone()
    if publicacao is None:
        conexao.close()
        abort(404, description="Publicação não encontrada.")

    conexao.execute("DELETE FROM publicacoes WHERE id = ?", (id,))
    conexao.commit()
    conexao.close()
    flash("Publicação excluída", "sucesso")
    return redirect(url_for("index"))


inicializar_banco()


if __name__ == "__main__":
    modo_debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host="127.0.0.1", port=5000, debug=modo_debug)
