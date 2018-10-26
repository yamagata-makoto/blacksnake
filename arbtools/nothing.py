class Nothing:

    def __init__(self):
        pass

    def __getattr__(self, name):
        return Nothing()

    def __getitem__(self, name):
        return Nothing()

    def __call__(self, *argc, **argv):
        return Nothing()



