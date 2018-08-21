import confight


class Config():

    data = {}

    @classmethod
    def load_data(cls):
        if cls.data:
            return
        cls.data.update(confight.load_app('lxd-image-server'))
