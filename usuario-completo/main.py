from flask import Flask, render_template, request, flash, redirect, url_for,session
import fdb
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'Aqui_e_a_chave_da_turma_a'

host = 'localhost'
database = r'C:\Users\marco\Downloads\banco-e-pycharm\BANCO.FDB'
user = 'SYSDBA'
password = 'SYSDBA'

con = fdb.connect(host=host, database=database, user=user, password=password)

@app.route('/')
def index():
    return render_template('login_usuario.html')


@app.route('/lista_livros')
def lista_livros():
    cursor = con.cursor() #abrindo o cursor

    cursor.execute("""SELECT l.id_livro,l.NOME, l.AUTOR, l.ANO_PUBLICACAO 
                            FROM LIVRO l 
                            order by l.nome """)

    livros = cursor.fetchall()

    cursor.close()
    return render_template('livros.html', livros=livros)

@app.route('/novo')
def novo():
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login_usu'))
    else:
        return render_template('novo.html')

@app.route('/criar', methods=['GET','POST'])
def criar():
    if request.method == 'GET':
        return render_template('novo.html')
    nome = request.form['titulo']
    autor = request.form['autor']
    ano_publicacao = request.form['ano_publicacao']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT 1 FROM LIVRO l WHERE nome = ?""", (nome,))
        if cursor.fetchone():
            flash('Erro: Livro já cadastrado')
            return redirect(url_for('novo'))

        cursor.execute( """ INSERT INTO livro (nome,autor, ano_publicacao)
                            VALUES (?, ? ,?) RETURNING ID_LIVRO""", (nome, autor, ano_publicacao))

        id_livro = cursor.fetchone()[0]
        con.commit()
        arquivo = request.files['imagem']
        arquivo.save(f'uploads/livro{id_livro}.jpg')

        flash("Livro cadastrado com sucesso")
        return redirect(url_for('lista_livros'))

    except Exception as e:
        flash(f"Ocorreu um error -> {e}")
        con.rollback()
        return redirect(url_for('novo'))

    finally:
        cursor.close()



@app.route('/editar/<int:id>', methods=['GET','POST'])
def editar(id):
    cursor = con.cursor()
    try:
        cursor.execute("""SELECT id_livro, nome, autor, ano_publicacao from livro WHERE ID_LIVRO = ?""", (id,))
        livro = cursor.fetchone()
        print(livro)

        if not livro:
            flash('Livro não encontrado')
            return redirect(url_for('lista_livros'))

        if request.method == 'POST':
            nome = request.form['titulo']
            autor = request.form['autor']
            ano_publicacao = request.form['ano_publicacao']

            cursor.execute(""" UPDATE LIVRO SET nome = ?, autor = ?, ano_publicacao = ?
                               where id_livro = ?""", (nome, autor, ano_publicacao, id))
            con.commit()
            flash("Livro editado com sucesso")
            return redirect(url_for('lista_livros'))

        return render_template('editar.html', livro=livro)

    except Exception as e:
            con.rollback()
            flash(f"Ocorreu um error -> {e}")
            return redirect(url_for('lista_livros'))


    finally:
        cursor.close()

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    cursor = con.cursor()
    try:
        cursor.execute("""DELETE FROM livro WHERE ID_LIVRO = ?""", (id,))
        con.commit()
        flash("Livro deletado com sucesso")
        return redirect(url_for('lista_livros'))

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um error -> {e}")
        return redirect(url_for('lista_livros'))
    finally:
        cursor.close()


@app.route('/lista_usu')
def lista_usu():
    cursor = con.cursor() #abrindo o cursor

    cursor.execute("""SELECT u.id_usuario,u.NOME, u.email, u.senha 
                            FROM usuario u
                            order by u.nome """)

    usuarios = cursor.fetchall()

    cursor.close()
    return render_template('usuarios.html', usuarios=usuarios)


@app.route('/login_usu', methods=['GET', 'POST'])
def login_usu():

    if request.method == 'GET':
        return render_template('login_usuario.html')

    email = request.form['email']
    senha = request.form['senha']

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT id_usuario,senha, tentativas FROM usuario u WHERE  u.email = ? """, (email,))
        usuario = cursor.fetchone()

        if not usuario:
            flash("Usuário não encontrado")
            return redirect(url_for('login_usu'))

        id_usuario, senha_hash, tentativas= usuario

        #se errar 3 vezes
        if tentativas >= 3:
            flash("Você atingiu o limite de tentativas!Conta bloqueada.")
            return redirect(url_for('login_usu'))

        if  usuario:
            if bcrypt.check_password_hash(senha_hash, senha):

            #se acertar a senha: zerar as tentativas
                cursor.execute("""UPDATE usuario set tentativas = 0
                               where id_usuario = ?""", (id_usuario,))
                con.commit()

                session['id_usuario'] = id_usuario

                flash('Conta logada')
                return redirect(url_for('lista_livros'))

            else:

                #Errou uma vez
                cursor.execute("""UPDATE usuario set tentativas = tentativas + 1
                               where id_usuario = ?""", (id_usuario,))
                con.commit()

                if tentativas + 1 >= 3:
                    flash("Você atingiu o limite de tentativas!Conta bloqueada.")
                else:
                    flash('Email ou senha inválida')
                return redirect(url_for('login_usu'))
        return render_template('login_usuario.html')


    except Exception as e:
        flash(f"Ocorreu um error -> {e}")
        con.rollback()
        return redirect(url_for('login_usu'))

    finally:
        cursor.close()


@app.route('/novo_usu')
def novo_usu():
    return render_template('novo_usuario.html')

# verificar senha forte
def senha_forte(senha):
    if len(senha) < 8:
        return False
    if senha.islower(): #letra minuscula
        return False
    if senha.isalpha(): # caracter especial
        return False
    if senha.isdigit():
        return False
    else:
        return True

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']

    if not senha_forte(senha):
        flash("Senha fraca! Precisa ter 8 ou mais caracteres, pelo menos uma letra maiúscula e um número")
        return redirect(url_for('novo_usu'))

    cursor = con.cursor()

    try:
        cursor.execute("""SELECT 1 FROM usuario u WHERE nome = ?""", (nome,))
        usuario = cursor.fetchone()
        if usuario:
            flash('Erro: Usuário já cadastrado')
            return redirect(url_for('novo_usu'))

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        cursor.execute( """ INSERT INTO usuario (nome,email,senha, tentativas)
                            VALUES (?, ? ,?,?)""", (nome, email, senha_hash, 0))

        con.commit()
        flash("Usuário cadastrado com sucesso")
        return redirect(url_for('login_usu'))


    except Exception as e:
        flash(f"Ocorreu um error -> {e}")
        con.rollback()
        return redirect(url_for('novo_usu'))

    finally:
        cursor.close()


@app.route('/editar_usuario/<int:id>', methods=['GET','POST'])
def editar_usuario(id):
    cursor = con.cursor()
    try:
        cursor.execute("""SELECT id_usuario, nome, email, senha from usuario WHERE ID_usuario = ?""", (id,))
        usuario = cursor.fetchone()


        if not usuario:
            flash('Usuário não encontrado')
            return redirect(url_for('lista_usu'))



        if request.method == 'POST':
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']

            senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

            cursor.execute(""" UPDATE usuario SET nome = ?, email = ?, senha = ?
                               where id_usuario = ?""", (nome, email, senha_hash, id))
            con.commit()
            flash("Usuário editado com sucesso")
            return redirect(url_for('lista_usu'))

        return render_template('editar_usuario.html', usuario=usuario)

    except Exception as e:
            con.rollback()
            flash(f"Ocorreu um error -> {e}")
            return redirect(url_for('lista_usu'))


    finally:
        cursor.close()

@app.route('/deletar_usuario/<int:id>', methods=['POST'])
def deletar_usuario(id):
    cursor = con.cursor()
    try:
        cursor.execute("""DELETE FROM usuario WHERE ID_usuario = ?""", (id,))
        con.commit()
        flash("Usuário deletado com sucesso")
        return redirect(url_for('lista_usu'))

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um error -> {e}")
        return redirect(url_for('lista_usu'))
    finally:
        cursor.close()

@app.route('/logout') #limpar da lista
def logout():
    if 'id_usuario' in session:
        session.pop('id_usuario')
        flash('Logout com sucesso')
    else:
        flash('Nenhuma conta está logada')

    return redirect(url_for('login_usu'))



if __name__ == '__main__':
    app.run(debug=True)