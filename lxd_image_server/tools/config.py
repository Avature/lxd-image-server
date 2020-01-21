import confight
from pathlib import Path

class Config():

    data = {}
    # where the configs are loaded from.
    paths = []

    # temporary object
    pathsAsDict = {}

    @classmethod
    def reload_data(cls):
        cls.data = {}
        cls.path = []
        cls.pathsAsDict = {}
        cls.load_data()

    original_load_paths = None

    @classmethod
    def confight_load_paths(cls, paths, finder=None, extension=None,
                   force_extension=False, **kwargs):
        for p in paths:
            p = str(Path(p).expanduser().resolve())
            cls.pathsAsDict[p] = True

        return cls.original_load_paths(paths, finder, extension, force_extension, **kwargs)

    @classmethod
    def load_data(cls):
        if cls.data:
            return
        cls.original_load_paths = confight.__dict__['load_paths']
        confight.__dict__['load_paths'] = cls.confight_load_paths

        cls.data.update(confight.load_app('lxd-image-server'))
        # allow non root installs as well
        cls.data.update(confight.load_user_app('lxd-image-server'))

        confight.__dict__['load_paths'] = cls.original_load_paths

        cls.paths = cls.pathsAsDict.keys()
        cls.pathsAsDict = {}
        # allow lack of any config file
        if 'mirrors' not in cls.data:
            cls.data['mirrors'] = {}


