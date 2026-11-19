import os
import secrets
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "publicacoes.db")


def conectar():
    conn = sqlite3.connect(BANCO)
    conn.row_factory = sqlite3.Row
    return conn


def criar_tabela():
    conn = conectar()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS publicacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            postada INTEGER NOT NULL DEFAULT 0
        )"""
    )
# banco antigo sem a coluna "postada"
    colunas = [coluna["name"] for coluna in conn.execute("PRAGMA table_info(publicacoes)")]
    if "postada" not in colunas:
        conn.execute("ALTER TABLE publicacoes ADD COLUMN postada INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()


def validar(titulo, conteudo):
    if titulo == "" or conteudo == "":
        return "O título e a descrição são obrigatórios."
    if len(titulo) > 100:
        return "O título não pode exceder 100 caracteres."
    if len(conteudo) > 2000:
        return "A descrição não pode exceder 2000 caracteres."
    return None


def buscar_ideia(id):
    conn = conectar()
    ideia = conn.execute("SELECT * FROM publicacoes WHERE id = ?", (id,)).fetchone()
    conn.close()
    if ideia is None:
        abort(404, description="Ideia não encontrada.")
    return ideia


@app.route("/")
def index():
    conn = conectar()
    ideias = conn.execute(
        "SELECT * FROM publicacoes ORDER BY postada ASC, id DESC"
    ).fetchall()
    conn.close()
    return render_template("index.html", ideias=ideias)


@app.route("/criar", methods=["POST"])
def criar():
    titulo = request.form.get("titulo", "").strip()
    conteudo = request.form.get("conteudo", "").strip()

    erro = validar(titulo, conteudo)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("index"))

    conn = conectar()
    conn.execute(
        "INSERT INTO publicacoes (titulo, conteudo) VALUES (?, ?)", (titulo, conteudo)
    )
    conn.commit()
    conn.close()

    flash("Ideia salva com sucesso!", "sucesso")
    return redirect(url_for("index"))


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    ideia = buscar_ideia(id)

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        conteudo = request.form.get("conteudo", "").strip()

        erro = validar(titulo, conteudo)
        if erro:
            flash(erro, "erro")
            return redirect(url_for("editar", id=id))

        conn = conectar()
        conn.execute(
            "UPDATE publicacoes SET titulo = ?, conteudo = ? WHERE id = ?",
            (titulo, conteudo, id),
        )
        conn.commit()
        conn.close()

        flash("Ideia atualizada com sucesso!", "sucesso")
        return redirect(url_for("index"))

    return render_template("editar.html", ideia=ideia)

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    buscar_ideia(id)

    conn = conectar()
    conn.execute("DELETE FROM publicacoes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Ideia excluída", "sucesso")
    return redirect(url_for("index"))


@app.route("/alternar-postada/<int:id>", methods=["POST"])
def alternar_postada(id):
    ideia = buscar_ideia(id)

    if ideia["postada"] == 1:
        novo_valor = 0
        mensagem = "Ideia desmarcada!"
    else:
        novo_valor = 1
        mensagem = "Ideia marcada como postada!"

    conn = conectar()
    conn.execute("UPDATE publicacoes SET postada = ? WHERE id = ?", (novo_valor, id))
    conn.commit()
    conn.close()

    flash(mensagem, "sucesso")
    return redirect(url_for("index"))


criar_tabela()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
