import confight


class Config():

    data = {}
    path = '/etc/lxd-image-server/config.toml'

    @classmethod
    def load_data(cls):
        if cls.data:
            return
        cls.data.update(confight.load([cls.path]))
