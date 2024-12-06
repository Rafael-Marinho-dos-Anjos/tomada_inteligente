
import matplotlib.pyplot as plt
from math import pi

from flask import render_template, request, Response, redirect, url_for
from markupsafe import Markup
from datetime import datetime

from app import app, db
from app.utils.plot import plot_n_save
from app.model.read import Read
from app.model.device import Device
from app.model.user import User
from app.control.users_manager import UserManager
from app.utils.device_card_generator import generate_card
from app.utils.device_token import gen_device_token


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
    reads_per_day = 28800
    for read in data:
        day = read.date_time.day

        if day in consume:
            consume[day] += read.s / reads_per_day
        else:
            consume[day] = read.s / reads_per_day
    
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
            error_msg=data["msg"] if "msg" in data.keys() else "",
            sucess_msg=data["suc_msg"] if "suc_msg" in data.keys() else ""
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


@app.route("/cadastro")
def new_user():
    data = request.args

    if "login" not in data.keys():
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else ""
        )
    
    if len(data["login"]) < 4:
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else "Login deve conter pelo menos 4 caracteres"
        )
    
    if len(data["usuario"]) < 4:
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else "O nome de usuario deve conter pelo menos 4 caracteres"
        )
    
    if data["senha_1"] != data["senha_2"]:
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else "As senhas não conferem"
        )
    
    if len(data["senha_1"]) < 8:
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else "A senha deve conter pelo menos 8 caracteres"
        )
    
    verify = User.query.filter(User.login == data["login"]).all()
    if len(verify) > 0:
        return render_template(
            "register.html",
            error_msg=data["msg"] if "msg" in data.keys() else "Login já em uso"
        )

    user = User(
        name = data["usuario"],
        login = data["login"],
        psswrd = data["senha_1"]
    )
    db.session.add(user)
    db.session.commit()

    return redirect(url_for(".login", suc_msg="Usuário cadastrado"))


@app.route("/logout/<token>")
def logout(token):
    manager = UserManager()
    try:
        manager.logout(token)
    finally:
        return redirect("/login")


@app.route("/tomadas/<token>")
def tomadas(token):
    user = UserManager().get_user_by_token(token)
    if user is None:
        return redirect(url_for(".login", msg="Sessão expirada"))

    devices = Device.query.filter(Device.user_id==user.id).all()

    if len(devices) > 0:
        info_devices = [
            [device.description, token, device.token] for device in devices
        ]
        cards = "".join([generate_card(*device) for device in info_devices])
    else:
        cards = "Não há nenhuma tomada cadastrada."
    
    return render_template(
        "devices.html",
        devices=Markup(cards),
        user=user.name,
        profile_img="images/no_profile.png",
        token=token
    )


@app.route("/tomadas/<token>/<cod_tomada>/")
def tomada(token, cod_tomada):
    user = UserManager().get_user_by_token(token)
    if user is None:
        return redirect(url_for(".login", msg="Sessão expirada"))
    
    date = datetime.today()
    begin = datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0)
    
    data = Read.query\
        .join(Device, Read.id_device == Device.id)\
        .add_columns(Read.s, Read.corr, Read.fp, Read.freq, Read.date_time)\
        .filter(Device.token==cod_tomada)\
        .filter(Read.date_time >= begin).order_by(Read.date_time).all()
    
    fp = list()
    fp_corr = list()
    s = list()
    q = list()
    q_corr = list()
    freq = list()
    for read in data:
        fp.append(read.fp)
        s.append(read.s)
        freq.append(read.freq)
        q_ = read.s * (1 - read.fp ** 2) ** 0.5
        q.append(q_)
        q_corr_ = q_ - read.corr
        q_corr.append(q_corr_)
        fp_corr_ = abs(1 - (q_corr_ / read.s) ** 2) ** 0.5
        fp_corr.append(fp_corr_)

    fp_graph_path = plot_n_save(
        [i for i in range(len(data))],
        fp,
        f"Fator de potência",
        "Leitura",
        "fp"
    )
    mean_fp = sum(fp)/len(fp)

    freq_graph_path = plot_n_save(
        [i for i in range(len(data))],
        freq,
        f"Frequência",
        "Leitura",
        "Hz"
    )
    mean_freq = sum(freq)/len(freq)
    
    fp_corr_graph_path = plot_n_save(
        [i for i in range(len(data))],
        fp_corr,
        f"Fator de potência corrigido",
        "Leitura",
        "fp"
    )
    mean_fp_corr = sum(fp_corr)/len(fp_corr)
    
    s_graph_path = plot_n_save(
        [i for i in range(len(data))],
        s,
        f"Potência Aparente",
        "Leitura",
        "W"
    )
    mean_s = sum(s)/len(s)
    
    q_graph_path = plot_n_save(
        [i for i in range(len(data))],
        q,
        f"Potência Reativa",
        "Leitura",
        "VA"
    )
    mean_q = sum(q)/len(q)
    
    q_corr_graph_path = plot_n_save(
        [i for i in range(len(data))],
        q_corr,
        f"Potência Reativa Corrigida",
        "Leitura",
        "VA"
    )
    mean_q_corr = sum(q_corr)/len(q_corr)

    return render_template(
        "device.html",
        user=user.name,
        profile_img="images/no_profile.png",
        fp_graph_path=fp_graph_path,
        fp_corr_graph_path=fp_corr_graph_path,
        s_graph_path=s_graph_path,
        q_graph_path=q_graph_path,
        q_corr_graph_path=q_corr_graph_path,
        freq_graph_path=freq_graph_path,
        mean_fp=f"{mean_fp:.2f}",
        mean_freq=f"{mean_freq:.2f}",
        mean_fp_corr=f"{mean_fp_corr:.2f}",
        mean_s=f"{mean_s:.2f}",
        mean_q=f"{mean_q:.2f}",
        mean_q_corr=f"{mean_q_corr:.2f}",
        token=token
    )


@app.route("/relatorio/<token>/")
def relatorio(token):
    user = UserManager().get_user_by_token(token)
    if user is None:
        return redirect(url_for(".login", msg="Sessão expirada"))
    
    date = datetime.today()
    begin = datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0)

    data = Read.query\
        .join(Device, Read.id_device == Device.id)\
        .join(User, Device.user_id == User.id)\
        .add_columns(Read.s, Read.corr, Read.fp, Read.freq, Read.date_time)\
        .filter(User.id==user.id)\
        .filter(Read.date_time >= begin).order_by(Read.date_time).all()
    
    fp = list()
    fp_corr = list()
    s = list()
    q = list()
    q_corr = list()
    freq = list()
    for read in data:
        fp.append(read.fp)
        s.append(read.s)
        freq.append(read.freq)
        q_ = read.s * (1 - read.fp ** 2) ** 0.5
        q.append(q_)
        q_corr_ = q_ - read.corr
        q_corr.append(q_corr_)
        fp_corr_ = abs(1 - (q_corr_ / read.s) ** 2) ** 0.5
        fp_corr.append(fp_corr_)

    fp_graph_path = plot_n_save(
        [i for i in range(len(data))],
        fp,
        f"Fator de potência",
        "Leitura",
        "fp"
    )
    mean_fp = sum(fp)/len(fp)

    freq_graph_path = plot_n_save(
        [i for i in range(len(data))],
        freq,
        f"Frequência",
        "Leitura",
        "Hz"
    )
    mean_freq = sum(freq)/len(freq)
    
    fp_corr_graph_path = plot_n_save(
        [i for i in range(len(data))],
        fp_corr,
        f"Fator de potência corrigido",
        "Leitura",
        "fp"
    )
    mean_fp_corr = sum(fp_corr)/len(fp_corr)
    
    s_graph_path = plot_n_save(
        [i for i in range(len(data))],
        s,
        f"Potência Aparente",
        "Leitura",
        "W"
    )
    mean_s = sum(s)/len(s)
    
    q_graph_path = plot_n_save(
        [i for i in range(len(data))],
        q,
        f"Potência Reativa",
        "Leitura",
        "VA"
    )
    mean_q = sum(q)/len(q)
    
    q_corr_graph_path = plot_n_save(
        [i for i in range(len(data))],
        q_corr,
        f"Potência Reativa Corrigida",
        "Leitura",
        "VA"
    )
    mean_q_corr = sum(q_corr)/len(q_corr)

    return render_template(
        "report.html",
        user=user.name,
        profile_img="images/no_profile.png",
        fp_graph_path=fp_graph_path,
        fp_corr_graph_path=fp_corr_graph_path,
        s_graph_path=s_graph_path,
        q_graph_path=q_graph_path,
        q_corr_graph_path=q_corr_graph_path,
        freq_graph_path=freq_graph_path,
        mean_fp=f"{mean_fp:.2f}",
        mean_freq=f"{mean_freq:.2f}",
        mean_fp_corr=f"{mean_fp_corr:.2f}",
        mean_s=f"{mean_s:.2f}",
        mean_q=f"{mean_q:.2f}",
        mean_q_corr=f"{mean_q_corr:.2f}",
        token=token
    )


@app.route("/nova_tomada/<token>")
def new_device(token):
    user = UserManager().get_user_by_token(token)
    if user is None:
        return redirect(url_for(".login", msg="Sessão expirada"))

    device_token = gen_device_token()
    while len(Device.query.filter(Device.token==device_token).all()) > 0:
        device_token = gen_device_token()

    device = Device(
        user_id = user.id,
        description = "",
        token = device_token
    )

    return render_template # TODO -> fazer a página


@app.route("/historico/<token>")
def historico(token):
    pass


@app.route("/visualize/<page>")
def visualize(page):
    devices = [
        ["tomada 1", "abcde", "HXVW"],
        ["tomada 2", "abcde", "HXVW"],
        ["tomada 3", "abcde", "HXVW"],
        ["tomada 4", "abcde", "HXVW"]
    ]
    cards = "".join([generate_card(*device) for device in devices])
    return render_template(page + ".html", devices=Markup(cards))


@app.route("/send_measure/<token>/", methods=['POST'])
def send_measure(token):
    data = request.form
    # 's', 'fp', 'freq', 'cap_base', 'cap_switch', 'v'
    cap_base = data["cap_base"].split('e')
    cap_base = int(cap_base[0]) * 10 ** int(int(cap_base[1]))

    cap = 0
    val = 1
    for i in range(len(data["cap_switch"])):
        if data["cap_switch"][-1-i] == "1":
            cap += val
        val *= 2

    cap *= cap_base

    corr = (float(data["v"]) ** 2) * 2 * pi * float(data["freq"]) * cap

    device = Device.query.filter(Device.token == token).first_or_404()
    read = Read(
        id_device = device.id,
        date_time = datetime.now(),
        fp = data["fp"],
        s = data["s"],
        corr = corr,
        freq = data["freq"]
    )

    db.session.add(read)
    db.session.commit()

    return Response(status=200)
