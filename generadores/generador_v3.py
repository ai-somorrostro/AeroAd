import csv
import random
import os
import unicodedata
from datetime import datetime, timedelta


# ============================================================
# CONFIGURACIÓN
# ============================================================

SEMILLA = 202606
random.seed(SEMILLA)

TOTAL_REGISTROS = 500_000
TOTAL_IDENTIDADES = 100_000

ANIO = 2026
MES = 6
DIAS_DEL_MES = 30

ARCHIVO_SALIDA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "captaciones_junio_2026_v3.txt"
)


# ============================================================
# CALIDAD DEL DATO
# ============================================================
#
# Estos porcentajes se aplican sobre los registros.
#
# NULL       -> campo con valor None
# VACIO      -> ""
# MAL_FORMATO -> formato incorrecto
#
# Los duplicados se generan como filas adicionales idénticas.
#

PORCENTAJE_NULOS = 0.025
PORCENTAJE_VACIOS = 0.020
PORCENTAJE_MAL_FORMATO = 0.020
PORCENTAJE_DUPLICADOS = 0.015


# ============================================================
# FABRICANTES
# ============================================================
#
# Los pesos representan la probabilidad relativa de cada marca.
# Las MAC son sintéticas.
#

FABRICANTES = {
    "Apple": {
        "peso": 18,
        "prefijos": [
            "3C:06:30",
            "3C:07:54",
            "3C:15:C2",
            "3C:22:FB",
            "3C:34:64"
        ]
    },

    "Samsung": {
        "peso": 16,
        "prefijos": [
            "00:16:32",
            "00:21:19",
            "00:24:54",
            "08:08:C2",
            "10:D5:42"
        ]
    },

    "Intel": {
        "peso": 15,
        "prefijos": [
            "DC:21:48",
            "00:1B:21",
            "00:1C:BF",
            "00:1C:C0",
            "3C:E9:F7"
        ]
    },

    "Lenovo": {
        "peso": 9,
        "prefijos": [
            "00:09:2D",
            "00:0A:F7",
            "28:D2:44",
            "54:EE:75",
            "98:FA:E3"
        ]
    },

    "HP": {
        "peso": 8,
        "prefijos": [
            "00:1A:4B",
            "00:21:5A",
            "3C:4A:92",
            "64:51:06",
            "84:34:97"
        ]
    },

    "Dell": {
        "peso": 7,
        "prefijos": [
            "00:14:22",
            "00:1E:4F",
            "18:03:73",
            "34:17:EB",
            "B0:83:FE"
        ]
    },

    "ASUS": {
        "peso": 6,
        "prefijos": [
            "00:0C:6E",
            "00:1A:92",
            "2C:56:DC",
            "30:5A:3A",
            "AC:9E:17"
        ]
    },

    "Xiaomi": {
        "peso": 5,
        "prefijos": [
            "00:9E:C8",
            "14:F6:5A",
            "28:6C:07",
            "34:CE:00",
            "50:64:2B"
        ]
    },

    "Huawei": {
        "peso": 4,
        "prefijos": [
            "00:18:82",
            "00:46:4B",
            "10:44:00",
            "48:46:F1",
            "A4:39:B3"
        ]
    },

    "Google": {
        "peso": 3,
        "prefijos": [
            "3C:5A:B4",
            "54:60:09",
            "94:EB:CD",
            "A4:77:33",
            "F4:F5:D8"
        ]
    },

    "Sony": {
        "peso": 3,
        "prefijos": [
            "00:13:A9",
            "00:1A:80",
            "00:24:8D",
            "30:52:CB",
            "AC:9B:0A"
        ]
    },

    "Acer": {
        "peso": 2,
        "prefijos": [
            "00:01:80",
            "00:09:DB",
            "00:1E:68",
            "04:7D:7B",
            "18:67:B0"
        ]
    },

    "Microsoft": {
        "peso": 2,
        "prefijos": [
            "00:15:5D",
            "28:18:78",
            "7C:1E:52",
            "98:5F:D3",
            "DC:53:7C"
        ]
    },

    "Motorola": {
        "peso": 2,
        "prefijos": [
            "00:04:56",
            "00:08:0E",
            "00:11:50",
            "3C:2E:F9",
            "48:2C:A0"
        ]
    }
}


# ============================================================
# SISTEMAS OPERATIVOS
# ============================================================

SISTEMAS_OPERATIVOS = {
    "Android": 40,
    "iOS": 35,
    "Windows 11": 12,
    "Windows 10": 6,
    "macOS": 7
}


# ============================================================
# OS POR FABRICANTE
# ============================================================
#
# Apple -> iOS o macOS
# Intel, Dell, Lenovo, HP, Sony, ASUS -> Windows (PC)
# Resto -> Android o Windows
#

FABRICANTES_PC = {
    "Intel", "Dell", "Lenovo", "HP", "Sony", "ASUS"
}


def os_por_fabricante(fabricante):
    """Devuelve el diccionario de SO válidos para un fabricante."""
    if fabricante == "Apple":
        return {
            "iOS": SISTEMAS_OPERATIVOS["iOS"],
            "macOS": SISTEMAS_OPERATIVOS["macOS"]
        }
    elif fabricante in FABRICANTES_PC:
        return {
            "Windows 11": SISTEMAS_OPERATIVOS["Windows 11"],
            "Windows 10": SISTEMAS_OPERATIVOS["Windows 10"]
        }
    else:
        return {
            "Android": SISTEMAS_OPERATIVOS["Android"],
            "Windows 11": SISTEMAS_OPERATIVOS["Windows 11"],
            "Windows 10": SISTEMAS_OPERATIVOS["Windows 10"]
        }


IDIOMAS = {
    "Android": {
        "es-ES": 25,
        "en-GB": 14,
        "en-US": 10,
        "fr-FR": 10,
        "de-DE": 9,
        "it-IT": 8,
        "pt-PT": 6,
        "nl-NL": 4,
        "pl-PL": 3,
        "ca-ES": 4,
        "sv-SE": 3,
        "es-MX": 4
    },

    "iOS": {
        "es-ES": 27,
        "en-GB": 14,
        "en-US": 12,
        "fr-FR": 10,
        "de-DE": 8,
        "it-IT": 8,
        "pt-PT": 6,
        "nl-NL": 4,
        "pl-PL": 3,
        "ca-ES": 3,
        "sv-SE": 2,
        "es-MX": 3
    },

    "Windows 11": {
        "es-ES": 24,
        "en-GB": 17,
        "en-US": 15,
        "fr-FR": 10,
        "de-DE": 10,
        "it-IT": 7,
        "pt-PT": 5,
        "nl-NL": 4,
        "pl-PL": 3,
        "sv-SE": 2,
        "es-MX": 3
    },

    "Windows 10": {
        "es-ES": 22,
        "en-GB": 17,
        "en-US": 16,
        "fr-FR": 10,
        "de-DE": 10,
        "it-IT": 8,
        "pt-PT": 5,
        "nl-NL": 4,
        "pl-PL": 3,
        "es-MX": 5
    },

    "macOS": {
        "es-ES": 22,
        "en-GB": 18,
        "en-US": 17,
        "fr-FR": 10,
        "de-DE": 9,
        "it-IT": 7,
        "pt-PT": 5,
        "nl-NL": 4,
        "sv-SE": 3,
        "es-MX": 5
    }
}


# ============================================================
# PAÍSES
# ============================================================

PAISES = {
    "ES": 28,
    "GB": 12,
    "FR": 10,
    "DE": 10,
    "IT": 8,
    "PT": 7,
    "US": 6,
    "NL": 4,
    "IE": 3,
    "BE": 3,
    "SE": 2,
    "DK": 2,
    "PL": 2,
    "CH": 1,
    "AT": 1,
    "MX": 1
}

PAISES_EUROPEOS = {
    "ES", "GB", "FR", "DE", "IT", "PT",
    "NL", "IE", "BE", "SE", "DK", "PL",
    "CH", "AT"
}


# ============================================================
# CONFIGURACIÓN POR SEMANA
# ============================================================
#
# Cada semana tiene una edad media diferente y un boost
# diferente para los países europeos.
#

SEMANAS = {
    1: {
        "edad_media": 25,
        "desviacion_edad": 8,
        "boost_europeo": 1.5
    },
    2: {
        "edad_media": 35,
        "desviacion_edad": 12,
        "boost_europeo": 1.3
    },
    3: {
        "edad_media": 50,
        "desviacion_edad": 10,
        "boost_europeo": 1.2
    },
    4: {
        "edad_media": 40,
        "desviacion_edad": 15,
        "boost_europeo": 1.4
    },
    5: {
        "edad_media": 30,
        "desviacion_edad": 10,
        "boost_europeo": 1.6
    }
}


# ============================================================
# DÍAS DE RUSH HOUR ALEATORIO
# ============================================================
#
# Se seleccionan días aleatorios del mes que tendrán
# rush hours adicionales (mediodía y noche).
#

NUMERO_DIAS_RUSH = 6
DIAS_RUSH_RANDOM = sorted(
    random.sample(
        range(1, DIAS_DEL_MES + 1),
        NUMERO_DIAS_RUSH
    )
)


# ============================================================
# NOMBRES
# ============================================================

NOMBRES = [
    "Alejandro", "Alba", "Álvaro", "Ana", "Andrea",
    "Antonio", "Beatriz", "Bruno", "Carlos", "Carmen",
    "Claudia", "Daniel", "David", "Diego", "Elena",
    "Elisa", "Enrique", "Eva", "Fernando", "Gabriel",
    "Irene", "Javier", "Jorge", "José", "Laura",
    "Lucía", "Luis", "Manuel", "María", "Marta",
    "Miguel", "Natalia", "Nicolás", "Pablo", "Patricia",
    "Paula", "Raquel", "Rafael", "Sara", "Sergio",
    "Sofía", "Teresa", "Víctor",

    "Adam", "Amelia", "Arthur", "Charlotte", "Edward",
    "Eleanor", "Emily", "George", "Grace", "Harry",
    "Henry", "Isla", "Jack", "Jacob", "James",
    "Jessica", "Liam", "Oliver", "Olivia", "Oscar",
    "Sophie", "Thomas", "William",

    "Adrien", "Camille", "Chloé", "Clément", "Élodie",
    "Étienne", "Hugo", "Julien", "Léa", "Louis",
    "Manon", "Mathieu", "Pierre", "Théo",

    "Anna", "Ben", "Clara", "Felix", "Finn",
    "Friedrich", "Greta", "Hannah", "Jonas",
    "Johanna", "Karl", "Klara", "Leon", "Lena",
    "Max", "Maximilian", "Paul",

    "Alessandro", "Alessia", "Chiara", "Davide",
    "Federico", "Francesca", "Gabriele", "Giulia",
    "Lorenzo", "Marco", "Matteo", "Simone",
    "Valentina",

    "Carolina", "Diogo", "Duarte", "Inês", "João",
    "Leonor", "Mafalda", "Mariana", "Rita",
    "Rodrigo", "Tiago",

    "Anne", "Erik", "Jens", "Karin", "Lars",
    "Lotte", "Maja", "Niels", "Sven",

    "Aleksandra", "Jakub", "Jan", "Katarzyna",
    "Krzysztof", "Marek", "Mateusz", "Piotr",
    "Tomasz",

    "Aisha", "Amir", "Fatima", "Hassan", "Layla",
    "Omar", "Rania", "Youssef", "Mei", "Hana",
    "Kenji", "Yuki", "Arjun", "Priya", "Rahul",
    "Sanjay"
]


# ============================================================
# APELLIDOS
# ============================================================

APELLIDOS = [
    "García", "Martínez", "López", "Sánchez",
    "González", "Rodríguez", "Fernández", "Pérez",
    "Gómez", "Martín", "Jiménez", "Ruiz", "Hernández",
    "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero",
    "Alonso", "Navarro", "Torres", "Domínguez",
    "Vázquez", "Ramos", "Ramírez", "Ortega",
    "Delgado", "Castro", "Ortiz",

    "Smith", "Jones", "Taylor", "Brown", "Williams",
    "Wilson", "Evans", "Thomas", "Roberts", "Johnson",
    "Lewis", "Walker", "Robinson", "Wood", "Thompson",
    "White", "Watson", "Murphy", "Kelly", "Ryan",

    "Martin", "Bernard", "Dubois", "Thomas", "Robert",
    "Richard", "Petit", "Durand", "Leroy", "Moreau",
    "Simon", "Laurent", "Michel",

    "Müller", "Schmidt", "Schneider", "Fischer",
    "Weber", "Meyer", "Wagner", "Becker", "Schulz",
    "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter",
    "Klein",

    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi",
    "Romano", "Colombo", "Ricci", "Marino", "Greco",
    "Bruno", "Gallo", "Conti", "De Luca", "Costa",

    "Silva", "Santos", "Ferreira", "Pereira",
    "Oliveira", "Rodrigues", "Martins", "Sousa",

    "Jansen", "De Vries", "Van den Berg", "Van Dijk",
    "Bakker", "Visser", "Smit", "Meijer",

    "Andersson", "Johansson", "Karlsson", "Nilsson",
    "Eriksson", "Larsson", "Olsson", "Persson",
    "Hansen", "Nielsen",

    "Kowalski", "Nowak", "Wójcik", "Kowalczyk",
    "Kamiński", "Lewandowski", "Zieliński",
    "Szymański", "Dąbrowski",

    "Hassan", "Khan", "Patel", "Shah", "Singh",
    "Kumar", "Gupta", "Chen", "Wang", "Zhang",
    "Tanaka", "Suzuki"
]


# ============================================================
# DOMINIOS
# ============================================================

DOMINIOS_EMAIL = [
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "icloud.com",
    "proton.me"
]


# ============================================================
# FUNCIONES DE ELECCIÓN
# ============================================================

def elegir(diccionario):
    valores = list(diccionario.keys())
    pesos = list(diccionario.values())

    return random.choices(
        valores,
        weights=pesos,
        k=1
    )[0]


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar(texto):

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    return texto.lower()


# ============================================================
# EMAIL
# ============================================================

def generar_email(nombre, apellido):

    nombre = normalizar(nombre)

    apellido = normalizar(
        apellido
    ).replace(
        " ",
        ""
    )

    dominio = random.choice(
        DOMINIOS_EMAIL
    )

    return (
        f"{nombre}.{apellido}"
        f"@{dominio}"
    )


def email_mal_formado(email):

    tipo = random.randint(
        1,
        7
    )

    if tipo == 1:
        return email.replace(
            "@",
            ""
        )

    if tipo == 2:
        return email.replace(
            ".com",
            ".con"
        )

    if tipo == 3:
        return email.replace(
            "gmail",
            "gmial"
        )

    if tipo == 4:
        return email.replace(
            "gmail",
            "gmal"
        )

    if tipo == 5:
        return email.replace(
            "@",
            "@@"
        )

    if tipo == 6:
        partes = email.split("@")

        if len(partes) == 2:
            return (
                partes[0]
                + "@"
                + partes[1]
                + "."
            )

    return email.replace(
        ".",
        "..",
        1
    )


# ============================================================
# MAC
# ============================================================

def generar_mac(fabricante=None):

    if fabricante is None:
        fabricante = elegir({
            marca: datos["peso"]
            for marca, datos
            in FABRICANTES.items()
        })

    prefijo = random.choice(
        FABRICANTES[fabricante]["prefijos"]
    )

    resto = ":".join(
        f"{random.randint(0, 255):02X}"
        for _ in range(3)
    )

    return (
        f"{prefijo}:{resto}",
        fabricante
    )


# ============================================================
# SEMANA
# ============================================================

def obtener_semana(dia):
    """Devuelve la semana (1-5) del mes para un día dado."""
    return min(5, (dia - 1) // 7 + 1)


# ============================================================
# EDAD POR SEMANA
# ============================================================

def generar_edad_semana(semana):
    """Genera una edad basada en la distribución de la semana."""
    config = SEMANAS[semana]
    edad = int(random.gauss(
        config["edad_media"],
        config["desviacion_edad"]
    ))
    return max(15, min(85, edad))


# ============================================================
# PAÍS POR SEMANA
# ============================================================

def generar_pais_semana(semana):
    """Genera un país con boost europeo según la semana."""
    config = SEMANAS[semana]
    boost = config["boost_europeo"]

    pesos_ajustados = {}
    for pais, peso in PAISES.items():
        if pais in PAISES_EUROPEOS:
            pesos_ajustados[pais] = int(peso * boost)
        else:
            pesos_ajustados[pais] = peso

    return elegir(pesos_ajustados)


# ============================================================
# IDENTIDAD
# ============================================================

def crear_identidad():

    nombre = random.choice(
        NOMBRES
    )

    apellido = random.choice(
        APELLIDOS
    )

    nombre_completo = (
        f"{nombre} {apellido}"
    )

    email = generar_email(
        nombre,
        apellido
    )

    # Asignar una semana aleatoria a esta identidad
    semana = random.randint(1, 5)

    edad = generar_edad_semana(semana)

    pais = generar_pais_semana(semana)

    # Primero elegimos el fabricante y luego un SO compatible
    fabricante = elegir({
        marca: datos["peso"]
        for marca, datos
        in FABRICANTES.items()
    })

    sistema = elegir(
        os_por_fabricante(fabricante)
    )

    idioma = elegir(
        IDIOMAS[sistema]
    )

    return {
        "Nombre": nombre_completo,
        "Email": email,
        "Edad": edad,
        "Pais": pais,
        "OS": sistema,
        "Idioma": idioma,
        "_semana": semana,
        "_fabricante": fabricante
    }


# ============================================================
# HORA
# ============================================================

def generar_hora(dia=None):
    """
    Genera una hora en segundos desde medianoche.
    
    Si el día es un día de rush aleatorio, se añaden
    franjas adicionales de mediodía y noche.
    """

    es_dia_rush = (
        dia is not None
        and dia in DIAS_RUSH_RANDOM
    )

    if es_dia_rush:
        # En días de rush: más franjas horarias
        periodo = random.choices(
            [
                "manana",
                "tarde",
                "mediodia",
                "noche"
            ],
            weights=[
                30,
                30,
                20,
                20
            ],
            k=1
        )[0]
    else:
        # Días normales: 45% mañana, 40% tarde, 15% resto
        periodo = random.choices(
            [
                "manana",
                "tarde",
                "resto"
            ],
            weights=[
                45,
                40,
                15
            ],
            k=1
        )[0]

    if periodo == "manana":

        inicio = (
            7 * 3600
            + 30 * 60
        )

        fin = (
            9 * 3600
            + 30 * 60
        )

    elif periodo == "tarde":

        inicio = (
            18 * 3600
        )

        fin = (
            20 * 3600
        )

    elif periodo == "mediodia":

        inicio = (
            12 * 3600
        )

        fin = (
            14 * 3600
        )

    elif periodo == "noche":

        inicio = (
            21 * 3600
        )

        fin = (
            23 * 3600
            + 59 * 60
        )

    else:

        tramos = [
            (
                0,
                7 * 3600
                + 29 * 60
            ),

            (
                9 * 3600
                + 31 * 60,
                17 * 3600
                + 59 * 60
            ),

            (
                20 * 3600
                + 1 * 60,
                23 * 3600
                + 59 * 60
            )
        ]

        inicio, fin = random.choice(
            tramos
        )

    return random.randint(
        inicio,
        fin
    )


# ============================================================
# FECHA
# ============================================================

def generar_fecha():

    dia = random.randint(
        1,
        DIAS_DEL_MES
    )

    segundos = generar_hora(dia)

    return (
        datetime(
            ANIO,
            MES,
            dia
        )
        + timedelta(
            seconds=segundos
        )
    )


# ============================================================
# RECURRENCIA
# ============================================================

def numero_de_captaciones():

    valor = random.random()

    if valor < 0.45:
        return 1

    if valor < 0.70:
        return random.randint(
            2,
            3
        )

    if valor < 0.88:
        return random.randint(
            4,
            7
        )

    if valor < 0.96:
        return random.randint(
            8,
            15
        )

    return random.randint(
        16,
        30
    )


# ============================================================
# CREAR CAPTACIONES
# ============================================================

def generar_captaciones_persona(
    persona,
    cantidad
):

    captaciones = []

    fecha_base = generar_fecha()

    for i in range(
        cantidad
    ):

        if i == 0:

            fecha = fecha_base

        else:

            tipo = random.random()

            # Login aproximadamente una hora después
            if tipo < 0.35:

                fecha = (
                    fecha_base
                    + timedelta(
                        minutes=random.randint(
                            45,
                            90
                        )
                    )
                )

            # Otra sesión durante el mismo día
            elif tipo < 0.60:

                fecha = (
                    fecha_base
                    + timedelta(
                        minutes=random.randint(
                            120,
                            720
                        )
                    )
                )

            # Otra visita otro día
            else:

                fecha = (
                    fecha_base
                    + timedelta(
                        days=random.randint(
                            1,
                            20
                        )
                    )
                )

            # Si cae fuera de junio,
            # generamos otra fecha dentro del mes.
            if fecha.month != MES:

                fecha = generar_fecha()

        mac, fabricante = generar_mac(
            persona["_fabricante"]
        )

        captaciones.append({
            "Hora de la captación":
                fecha.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "MAC":
                mac,

            "Fabricante":
                fabricante,

            "Nombre":
                persona["Nombre"],

            "OS del sistema":
                persona["OS"],

            "Idioma del OS":
                persona["Idioma"],

            "Rango de edad":
                persona["Edad"],

            "Email":
                persona["Email"],

            "Pais de origen":
                persona["Pais"]
        })

    return captaciones


# ============================================================
# INTRODUCIR PROBLEMAS DE CALIDAD
# ============================================================

def aplicar_error_campo(valor, tipo):

    if tipo == "nulo":
        return None

    if tipo == "vacio":
        return ""

    if tipo == "mal_formato":

        if valor is None:
            return valor

        if tipo == "mal_formato":
            return str(valor) + "???"

    return valor


def introducir_calidad(registro):

    campos = list(
        registro.keys()
    )

    # Nulos
    if random.random() < PORCENTAJE_NULOS:

        campo = random.choice(
            campos
        )

        registro[campo] = None

    # Vacíos
    if random.random() < PORCENTAJE_VACIOS:

        campo = random.choice(
            campos
        )

        registro[campo] = ""

    # Mal formato
    if random.random() < PORCENTAJE_MAL_FORMATO:

        campo = random.choice(
            campos
        )

        valor = registro[campo]

        if valor not in (
            None,
            ""
        ):

            if campo == "Rango de edad":

                registro[campo] = (
                    "edad_" + str(valor)
                )

            elif campo == "Pais de origen":

                registro[campo] = (
                    "ESP"
                )

            elif campo == "MAC":

                registro[campo] = (
                    "MAC-INVALIDA"
                )

            elif campo == "Email":

                registro[campo] = (
                    email_mal_formado(
                        str(valor)
                    )
                )

            elif campo == "Hora de la captación":

                registro[campo] = (
                    "fecha_incorrecta"
                )

            else:

                registro[campo] = (
                    str(valor)
                    + "???"
                )

    return registro


# ============================================================
# INFLUXDB LINE PROTOCOL
# ============================================================

def escapar_tag(valor):
    """Escapa caracteres especiales en valores de tags para InfluxDB."""
    if valor is None:
        return ""
    valor = str(valor)
    valor = valor.replace(",", "\\,")
    valor = valor.replace("=", "\\=")
    valor = valor.replace(" ", "\\ ")
    return valor


def escapar_field(valor):
    """Escapa caracteres especiales en valores de fields para InfluxDB."""
    if valor is None:
        return '""'
    valor = str(valor)
    valor = valor.replace("\\", "\\\\")
    valor = valor.replace('"', '\\"')
    return f'"{valor}"'


def a_influxdb_line(registro):
    """Convierte un registro a formato InfluxDB line protocol."""
    # Tags (metadatos indexados)
    tags = []
    for campo in [
        "Fabricante",
        "OS del sistema",
        "Idioma del OS",
        "Pais de origen",
        "MAC"
    ]:
        valor = registro.get(campo)
        if valor is not None and valor != "":
            tags.append(
                f"{campo}={escapar_tag(valor)}"
            )

    # Fields (valores de datos)
    fields = []
    for campo in [
        "Nombre",
        "Rango de edad",
        "Email"
    ]:
        valor = registro.get(campo)
        if valor is not None and valor != "":
            fields.append(
                f"{campo}={escapar_field(valor)}"
            )

    # Timestamp en nanosegundos
    timestamp = registro.get(
        "Hora de la captación"
    )
    ts_ns = None
    if timestamp:
        try:
            dt = datetime.strptime(
                timestamp,
                "%Y-%m-%d %H:%M:%S"
            )
            ts_ns = int(
                dt.timestamp() * 1_000_000_000
            )
        except (ValueError, TypeError):
            pass

    tag_set = ",".join(tags)
    field_set = ",".join(fields)

    linea = "captaciones"
    if tag_set:
        linea += f",{tag_set}"
    linea += f" {field_set}"
    if ts_ns:
        linea += f" {ts_ns}"

    return linea


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 65)
    print("GENERADOR DE CAPTACIONES WIFI SINTÉTICAS")
    print("=" * 65)
    print()

    print(
        f"Registros objetivo: "
        f"{TOTAL_REGISTROS:,}"
    )

    print(
        f"Identidades: "
        f"{TOTAL_IDENTIDADES:,}"
    )

    print(
        f"Periodo: "
        f"01/06/{ANIO} - "
        f"30/06/{ANIO}"
    )

    print(
        f"Días de rush aleatorio: "
        f"{DIAS_RUSH_RANDOM}"
    )

    print()

    # --------------------------------------------------------
    # Generar identidades
    # --------------------------------------------------------

    print(
        "Generando identidades..."
    )

    identidades = []

    for _ in range(
        TOTAL_IDENTIDADES
    ):

        identidades.append(
            crear_identidad()
        )

    print(
        f"{len(identidades):,} "
        f"identidades creadas."
    )

    # --------------------------------------------------------
    # Generar captaciones
    # --------------------------------------------------------

    print(
        "Generando captaciones..."
    )

    registros = []

    while len(registros) < TOTAL_REGISTROS:

        persona = random.choice(
            identidades
        )

        cantidad = (
            numero_de_captaciones()
        )

        captaciones = (
            generar_captaciones_persona(
                persona,
                cantidad
            )
        )

        for registro in captaciones:

            registros.append(
                registro
            )

            if len(registros) >= TOTAL_REGISTROS:
                break

    # --------------------------------------------------------
    # Crear duplicados reales
    # --------------------------------------------------------

    numero_duplicados = int(
        TOTAL_REGISTROS
        * PORCENTAJE_DUPLICADOS
    )

    print(
        f"Creando aproximadamente "
        f"{numero_duplicados:,} duplicados..."
    )

    # Seleccionamos registros existentes
    # y los duplicamos literalmente.
    #
    # Después recortamos a exactamente
    # TOTAL_REGISTROS.

    duplicados = random.sample(
        registros,
        min(
            numero_duplicados,
            len(registros)
        )
    )

    registros.extend(
        duplicados
    )

    random.shuffle(
        registros
    )

    registros = registros[
        :TOTAL_REGISTROS
    ]

    # --------------------------------------------------------
    # Aplicar errores
    # --------------------------------------------------------

    print(
        "Introduciendo problemas "
        "de calidad..."
    )

    registros_finales = []

    for registro in registros:

        copia = registro.copy()

        copia = introducir_calidad(
            copia
        )

        registros_finales.append(
            copia
        )

    # --------------------------------------------------------
    # Orden cronológico
    # --------------------------------------------------------
    #
    # Los registros con fecha incorrecta o nula se colocan
    # al final.

    def clave_fecha(registro):

        valor = (
            registro[
                "Hora de la captación"
            ]
        )

        if not valor:
            return datetime.max

        try:

            return datetime.strptime(
                valor,
                "%Y-%m-%d %H:%M:%S"
            )

        except ValueError:

            return datetime.max

    registros_finales.sort(
        key=clave_fecha
    )

    # --------------------------------------------------------
    # Guardar CSV
    # --------------------------------------------------------

    print(
        "Guardando en formato "
        "InfluxDB line protocol..."
    )

    with open(
        ARCHIVO_SALIDA,
        "w",
        encoding="utf-8"
    ) as archivo:

        for registro in registros_finales:

            linea = a_influxdb_line(
                registro
            )

            archivo.write(
                linea + "\n"
            )

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("GENERACIÓN FINALIZADA")
    print("=" * 65)
    print()

    print(
        f"Archivo: {ARCHIVO_SALIDA}"
    )

    print(
        f"Registros: "
        f"{len(registros_finales):,}"
    )

    print(
        f"Identidades generadas: "
        f"{len(identidades):,}"
    )

    print(
        f"Periodo: "
        f"01/06/{ANIO} - "
        f"30/06/{ANIO}"
    )

    print(
        f"Días de rush aleatorio: "
        f"{DIAS_RUSH_RANDOM}"
    )

    print()

    print(
        "Características incluidas:"
    )

    print(
        "  - Fabricantes con diferentes pesos"
    )

    print(
        "  - Identidades reutilizables"
    )

    print(
        "  - Múltiples dispositivos por identidad"
    )

    print(
        "  - Edad media diferente por semana"
    )

    print(
        "  - Nacionalidades diferentes por semana"
    )

    print(
        "  - Boost europeo en nacionalidades"
    )

    print(
        "  - Días de rush aleatorio con horas extra"
    )

    print(
        "  - Registros nulos"
    )

    print(
        "  - Campos vacíos"
    )

    print(
        "  - Datos con formato incorrecto"
    )

    print(
        "  - Registros duplicados"
    )

    print()
    print(
        "El archivo se ha creado en formato "
        "InfluxDB line protocol, listo para importar "
        "con influx write o curl."
    )
    print()


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    main()