

usuarios = ["Johanna", "Antonia", "PEPE"]


if usuarios:
    print("Ya hay usuarios registrados ")

    while True:
        print("Selecione su USuarios")
        for i,nombre in enumerate(usuarios):
            print(i,".", nombre)
        
        n = input("Opcion ")

        if n == '0':
            print("Bienvenida Joanna ")
        elif n == '1':
            print("Bienvenida Antonia ")
        elif n == '2':
            print("Bienvenida Pepe ")
        else:
            print("Usiaro incorrecto ")
            break
else: 
    print("Primero debe registrar USuarios")


