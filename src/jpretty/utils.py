import datetime


def nice_time(dt):
    dt = dt.astimezone()
    now = datetime.datetime.now()
    if dt.date() != now.date():
        return dt.strftime("%m-%d %I:%M%p").lower()
    else:
        return dt.strftime("%I:%M%p").lower()


class DictAttr:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, name):
        return self.d[name]
