import unicodedata

def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))
