class DatetimeBucketer:
    def __init__(self, window):
        self.window = window
        # The set of good instants
        self.instants = set()
        # Map rounded times to good instants
        self.rounds = {}

    def roundings(self, dt):
        for jitter in [0, self.window / 2]:
            yield round((dt.timestamp() + jitter) / self.window)

    def defuzz(self, dt):
        if dt in self.instants:
            return dt

        for rounded in self.roundings(dt):
            instant = self.rounds.get(rounded)
            if instant is not None:
                return instant

        self.instants.add(dt)
        for rounded in self.roundings(dt):
            self.rounds[rounded] = dt

        return dt
