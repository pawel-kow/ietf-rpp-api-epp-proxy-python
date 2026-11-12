import time


class Pacer:
    """Spaces the requests of each registrar evenly, so a run stays under a backend's limit of requests per minute.

    The limit is the environment's `rpp_requests_per_minute` per registrar, shared by the `workers` processes of the
    run, each of which paces its own requests to its share.
    """

    def __init__(self, requests_per_minute: int | None, workers: int, slot_of, clock=time.monotonic, sleep=time.sleep):
        self.interval = 60.0 * workers / requests_per_minute if requests_per_minute else 0.0
        self.slot_of = slot_of
        self.clock = clock
        self.sleep = sleep
        self.last: dict[str, float] = {}

    def wait(self, headers: dict) -> None:
        if not self.interval:
            return
        slot = self.slot_of(headers.get("Authorization", ""))
        if slot is None:
            return
        now = self.clock()
        due = self.last.get(slot, now - self.interval) + self.interval
        if due > now:
            self.sleep(due - now)
            now = due
        self.last[slot] = now
