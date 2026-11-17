class ErrorValidacion(Exception):
    def __init__(self, mensaje, campo=None, estado=400):
        self.mensaje, self.campo, self.estado = mensaje, campo, estado
