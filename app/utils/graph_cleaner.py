import os
from datetime import datetime, timedelta

from app.utils.singleton import SingletonMeta


class Cleaner(metaclass=SingletonMeta):
    def __init__(self):
        self.__images = dict()
        self.__time_to_del = timedelta(seconds=15)
        self.__img_path = "app/static/images/graphs"

    def new_image(self, img_name):
        self.__images[img_name] = datetime.now()

    def recicle(self):
        now = datetime.now()
        dropout = list()
        for img_name in self.__images.keys():
            if now - self.__images[img_name] >= self.__time_to_del:
                os.remove(
                    os.path.join(self.__img_path, img_name)
                )
                dropout.append(img_name)
        
        for img in dropout:
            self.__images.pop(img)

        for img_name in os.listdir(self.__img_path):
            if img_name not in self.__images.keys():
                self.__images[img_name] = datetime.now()
