BACKEND = "{backend}"


class BackendRequirement(ValueError):
    """A value that is not in the form the backend requires. The mapper says what, writing `{backend}` where the
    backend is named, and `detail` names it, as the mapper need not know which backend it is."""

    def __init__(self, template: str):
        super().__init__(template.replace(BACKEND, "the backend"))
        self.template = template

    def detail(self, backend_name: str) -> str:
        return self.template.replace(BACKEND, backend_name)
