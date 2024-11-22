
import matplotlib.pyplot as plt

from flask import render_template, request, Response, redirect, url_for
from datetime import datetime

from app import app, db
from app.utils.plot import plot_n_save
from app.model.read import Read
from app.model.device import Device
from app.model.user import User
from app.control.users_manager import UserManager


@app.route("/")
def init():
    return redirect("/login")


@app.route("/<token>")
def index(token):
    user = UserManager().get_user_by_token(token)
    if user is None:
        return redirect(url_for(".login", msg="Sessão expirada"))

    date = datetime.today()
    begin = datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0)
    months = (
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    )

    data = Read.query\
        .join(Device, Read.id_device == Device.id)\
        .join(User, Device.user_id == User.id)\
        .add_columns(Read.s, Read.fp, Read.date_time)\
        .filter(User.id==user.id)\
        .filter(Read.date_time >= begin).all()
    
    consume = dict()
    for read in data:
        day = read.date_time.day

        if day in consume:
            consume[day] += read.s
        else:
            consume[day] = read.s
    
    data = list()
    days = sorted(consume.keys())
    for day in days:
        data.append(consume[day])

    graph_path = plot_n_save(
        days,
        data,
        f"Consumo: {months[date.month - 1]}",
        "Dia",
        "Energia (kVAh)"
    )
    
    return render_template(
        "index.html",
        user=user.name,
        profile_img="images/no_profile.png",
        graph_path=graph_path,
        token=token
    )

@app.route("/login")
def login():
    data = request.args

    if "usuario" not in data.keys():
        return render_template(
            "login.html",
            error_msg=data["msg"] if "msg" in data.keys() else ""
        )

    login = data["usuario"]
    psswrd = data["senha"]

    user = User.query.filter(User.login==login).filter(User.psswrd==psswrd).all()
    
    if len(user) == 0:
        return render_template("login.html", error_msg="Login ou senha inválido")
    else:
        manager = UserManager()
        token = manager.login(user[0])
        if not token:
            return render_template("login.html", error_msg="Usuário já se encontra logado")
        else:
            return redirect("/" + token)


@app.route("/logout/<token>")
def logout(token):
    manager = UserManager()
    try:
        manager.logout(token)
    finally:
        return redirect("/login")


@app.route("/tomadas/<user>")
def tomadas(user):
    pass


@app.route("/historico/<user>")
def historico(user):
    pass


@app.route("/relatorio/<user>")
def relatorio(user):
    pass


@app.route("/send_read/<token>", methods=['POST'])
def send_read(token):
    data = request.form

    device = Device.query.filter(Device.token == token).first_or_404()
    read = Read(
        id_device = device.id,
        date_time = datetime.now(),
        fp = data["fp"],
        s = data["s"],
        corr = data["corr"],
        freq = data["freq"]
    )

    db.session.add(read)
    db.session.commit()

    return Response(status=200)
