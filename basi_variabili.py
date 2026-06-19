# 1. Le Stringhe (Text / str) - Vanno sempre tra virgolette
nome_studente = "Gennaro"
universita = "Salerno"

# 2. Gli Interi (Integers / int) - Numeri senza virgola
eta = 22
cfu_acquisiti = 96

# 3. I Float (Floating Point / float) - Numeri con la virgola (si usa il punto!)
media_voti = 23.0
altezza_metri = 1.85

# Stampiamo il valore e il TIPO di dato per capire cosa vede il computer
print("--- VERIFICA TIPI DI DATO ---")

print(nome_studente)
print(type(nome_studente))  # Ti dirà <class 'str'> (Stringa)

print(cfu_acquisiti)
print(type(cfu_acquisiti))  # Ti dirà <class 'int'> (Intero)

print(media_voti)
print(type(media_voti))  # Ti dirà <class 'float'> (Numero con virgola)


cfu_mancanti=180-cfu_acquisiti
print(cfu_mancanti)