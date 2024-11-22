from uuid import uuid4
from datetime import datetime, timedelta

from app.model.user import User
from app.utils.singleton import SingletonMeta


class UserManager(metaclass=SingletonMeta):
    def __init__(self, auto_logoff_time: int = None):
        self.__sessions = dict()
        self.__logged_in = set()

        if auto_logoff_time:
            self.__auto_logoff_time = timedelta(seconds=auto_logoff_time)
        else:
            self.__auto_logoff_time = timedelta(seconds=600)

    def login(self, user: User):
        if user.login in self.__logged_in:
            return False
        
        token = str(uuid4())
        while token in self.__sessions.keys():
            token = str(uuid4())

        self.__sessions[token] = {"user": user, "last_change": datetime.now()}
        self.__logged_in.add(user.login)

        return token

    def refresh(self, token: str):
        if token in self.__sessions:
            self.__sessions[token]["last_change"] = datetime.now()

    def logout(self, token: str):
        if token in self.__sessions:
            session = self.__sessions.pop(token)

            self.__logged_in.remove(session["user"].login)

    def get_user_by_token(self, token: str):
        if token in self.__sessions:
            return self.__sessions[token]["user"]
