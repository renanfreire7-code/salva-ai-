from datetime import datetime


class Clock:
    def now(self):
        return datetime.now().astimezone()

    def today(self):
        return self.now().date()
