from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import random, os
import pandas as pd
import json

app = Flask(__name__)

#llave para el manejo de sesiones
app.secret_key = 'boletasCoofisam'


# Tamaño del lote a recorrer
tamaño_lote = 500

# Diccionario para mantener un registro de las boletas asignadas a cada persona
boletas_asignadas_por_persona = {}

# Utiliza un diccionario para almacenar temporalmente los datos entre solicitudes
data_dict = {}

#Conjunto para llevar control de las agencias ganadoras, para llevar control del sorteo de 1 minuto de la felicidad, ya que la condicion del sorteo es que debe haber un ganador por agencia, por lo cual usamos un conjunto que no permite valores duplicados/repetidos
agencias_ganadoras = {}

#conjunto que agregará las boletas ganadoras para evitar que un mismo numero vuelva a ganar
boletasGanadoras = set()

personas_ganadoras = set()

#variable para guardar el numero total de oficinas que participaran en el sorteo
nroOficinas = 0

#guardamos el nombre del archivo de ahorros para que la condicion de que haya ganador por cada agencia solo se aplique para esa base de datos, el archivo excel debe tener ese nombre para que se aplique la condicion de haber un ganador por cada oficina
archivoAhorros = "19Sorteos"

# Añade un conjunto de boletas no aptas para ganar
boletas_no_aptas = set()

# Ruta principal para mostrar el resultado
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/subirArchivo", methods=["POST"])
def subirArchivo():
    global data_dict
    global nroOficinas
    
    #semilla para generar siempre los mismo numeros de boletas
    random.seed(123)
    
    #guarda en la variable el archivo que se subio por medio del formulario html
    archivo = request.files['archivosq']
        
    #guarda el nombre del archivo que se subio sin la extension
    nombre_archivo_original = os.path.splitext(archivo.filename)[0]
        
    # Lee el archivo y asigna el DataFrame
    df = pd.read_excel(archivo)
    
    #guarda la cantidad de boletas a generar, tomando la columna "NroBoletas" de la base en el archivo excel sumando los numeros de boletas de todas las personas que participan
    sumaNroBoletas = df['NroBoletas'].sum()
    
    #cuenta los valores únicos en la columna "agencia" de la base en excel.
    nroOficinas = df['agencia'].nunique()
    
    print(sumaNroBoletas)
    
    # Restablecer el diccionario al cargar un nuevo archivo
    data_dict = {}

    # Reiniciar el conjunto de boletas asignadas
    boletas_asignadas = set()

    #Función para asignar los nros de las boletas a cada persona, los parametros "nombre" y "cantidad_boletas" son los datos de los nombres y la cantidad de boletas a las que tiene derecho cada persona, dichos datos son sacados del archivo excel
    def asignar_boletas(nombre, cantidad_boletas):
        #se crea conjunto el cual guardara los numeros de las boletas asignadas a la persona, se usa un conjunto ya que no permite valores repetidos
        boletas_asignadas_a_la_persona = set()
        #mientras el numero de elementos del conjunto "boletas_asignadas_a_la_persona" es menor a "cantidad_boletas" el cual es el numero de boletas a las que tiene derecho cada persona, dato sacado del archivo excel, por lo cual mientras sea mejor generará numeros aleatorios y los agregará al conjunto
        while len(boletas_asignadas_a_la_persona) < cantidad_boletas:
            #variable que guarda los numeros generados, que van desde 1 hasta el numero total de boletas guardada en la variable "sumaNroBoletas" la cual tiene la suma total de boletas de todas las personas que participaran, adicionalmente aumento el rango en 200 numeros mas, para no dejar que el rango de numeros a generar sea igual al numero total de boletas, esto con el fin de optimizacion del codigo
            numero_boleta = random.randint(1, sumaNroBoletas + 200)
            #si el numero generado no está en el conjunto general "boletas_asignadas" y el conjunto "boletas_asignadas_a_la_persona" los agrega respectivamente
            if numero_boleta not in boletas_asignadas and numero_boleta not in boletas_asignadas_a_la_persona:
                boletas_asignadas_a_la_persona.add(numero_boleta)
                boletas_asignadas.add(numero_boleta)
        #crea diccionario teniendo como clave los nombres de la persona y como valor una lista con los nros de las boletas generados
        boletas_asignadas_por_persona[nombre] = list(boletas_asignadas_a_la_persona)

    # Iterar por lotes
    inicio = 0
    fin = tamaño_lote
    #se itera por lotes para optimizar el uso de memoria y no realizar toda la asignacion de boletas al mismo tiempo sino por partes, por lo cual mientras inicio sea menor a la longitud de "df" el cual es el tamaño total de registros del libro, crea un diccionario con las columnas "Nombres" haciendo slicing con "inicio" y "fin" como clave el mismo procedimiento asignando el nro de boletas a las que tiene derecho la persona
    while inicio < len(df):
        data_dict = dict(zip(df['Nombres'][inicio:fin], df['NroBoletas'][inicio:fin]))
        #Iterar a través del diccionario de datos traidos del archivo excel del lote actual, llamando a la funcion pasando como parametro el nombre y la cantidad de boletas a asignar
        for nombre, cantidad in data_dict.items():
            asignar_boletas(nombre, cantidad)

        #por cada iteracion actualizo los valores de las variables para iterar por lotes
        inicio = fin
        fin += tamaño_lote

    #agrega a la columna "BoletasAsignadas" tomando en cuenta el nombre de la persona, gracias a la funcion "map" la cual toma los valores de la columna "Nombres" y busca los valores que corresponden en el diccionario creado
    df['BoletasAsignadas'] = df['Nombres'].map(boletas_asignadas_por_persona)
        
    # Guarda el DataFrame modificado en un nuevo archivo plano txt concatenando el nombre del archivo subido con "Resultado", se guarda en txt debido a que en excel se alcanza el limite de caracteres a escribir en una columna de los numeros generados, por lo cual se pierde informacion, debido a esto se usa el formato csv (separado por comas) y se guarda en archivo plano
    df.to_csv(f'{nombre_archivo_original} Resultado.txt', index=False)

    #Agrega al diccionario como clave el nombre del archivo original que se sube a la pagina y como valor toma los registros y/o datos correspondientes del archivo lo que permite organizar y facilitar el acceso a la informacion de cada archivo subido en la pagina
    data_dict[nombre_archivo_original] = df.to_dict(orient='records')

    return redirect(url_for('importacion_excel'))
        
        
@app.route("/importacion_excel")
def importacion_excel():
    global data_dict

    #obtiene el último archivo subido desde el diccionario, verificando con el condicional que el diccionario no esté vacio, si no esta vacio seleccionando la ultima clave del diccionario que corresponde al ultimo archivo subido
    ultimo_archivo = list(data_dict.keys())[-1] if data_dict else None
    #utiliza la ultima clave del diccionario y obtiene los datos/valores asociados a la dicha clave y crea un dataframe con dichos datos
    df = pd.DataFrame(data_dict.get(ultimo_archivo, []))
    
    #redirige a la pagina "sorteo" y se pasa el df para poder mostrar los datos en la pagina
    return render_template("Sorteo.html", df=df)

@app.route('/descartar_boleta', methods=['POST'])
def descartar_boleta():
    global agencias_ganadoras
    
    #variable que guarda el numero de la boleta enviada desde el formulario html que descarta dicho nro los cuales no cumplen con las condiciones para ser ganador
    boleta = request.form.get('boleta')
    #añado el nro descartado por medio del formulario html al conjunto
    boletas_no_aptas.add(boleta)
    # Carga el diccionario de la sesión, Convierte agencias_ganadoras a un diccionario después de obtenerlo de la sesión
    agencias_ganadoras = json.loads(session.get('agencias_ganadoras', {}))
    #Comprension de diccionario que Convierte las claves a enteros nuevamente
    agencias_ganadoras = {int(k): v for k, v in agencias_ganadoras.items()}
    
    return redirect(url_for('importacion_excel'))


@app.route('/resultado', methods=['POST'])
def resultado():
    #declaro variables globales para poder acceder desde esta funcion a dichas variables
    global data_dict
    global agencias_ganadoras
    global archivoAhorros
    global boletasGanadoras
    global personas_ganadoras
    global boletas_no_aptas
    global nroOficinas
    
    print(nroOficinas)
    
    #Convierte agencias_ganadoras a una cadena antes de guardarla en la sesión
    session['agencias_ganadoras'] = json.dumps(agencias_ganadoras)
    
    # Reiniciar la semilla para seleccionar el número ganador en cada solicitud
    random.seed()

    #obtiene el último archivo subido desde el diccionario, verificando con el condicional que el diccionario no esté vacio, si no esta vacio seleccionando la ultima clave del diccionario que corresponde al ultimo archivo subido
    ultimo_archivo = list(data_dict.keys())[-1] if data_dict else None
    boletas_asignadas = set()
 
    #Itera sobre los registros asociados con el último archivo subido en el diccionario
    for record in data_dict.get(ultimo_archivo, []):
        #actualiza el conjunto de boletas generadas para tomar los datos de las boletas solamente del ultimo archivo que se subio
        boletas_asignadas.update(record['BoletasAsignadas'])

    ganador = None
    #Mientras no se haya encontrado un ganador, el bucle continuará hasta que se encuentre.
    while not ganador:
        #seleccion aleatoria de numero ganador de la lista que contiene todos los nros
        numero_ganador = random.choice(list(boletas_asignadas))       
        #recorre las claves y valores del diccionario "agencias_ganadoras"
        for agencia, boleta in list(agencias_ganadoras.items()):
            # Verifica si la boleta está en el conjunto de boletas no aptas
            if boleta in boletas_no_aptas:
                #elimina la "agencia" la cual es la clave del diccionario
                del agencias_ganadoras[agencia]
       
        #valida si "ultimo_archivo" es igual a "archivoAhorros", esto es para que si los valores son los mismos se aplique la condicion de que debe haber por lo menos un ganador por cada oficina, la 2da condicion valida si el nro de elementos del diccionario es menor a "nroOficinas" esta variable tiene el numero de oficinas que participan en el sorteo, y la 3ra condicion es para evitar que un mismo nro gane dos veces
        if ultimo_archivo == archivoAhorros and len(agencias_ganadoras) < nroOficinas and numero_ganador not in boletasGanadoras:
            #Determinar a quién pertenece el número ganador, recorriendo el diccionario del ultimo archivo que se subio el cual tiene como clave el nombre de la persona y como valor una lista donde estan los nros de las boletas asignadas a la persona
            for record in data_dict.get(ultimo_archivo, []):
                #si el nro generado esta en "BoletasAsignadas" el cual columna donde estan las listas con los numeros aleatorios generados para cada persona que participará en el sorteo y la 2da condicion valida si la persona no esta en el conjunto "personas_ganadoras" es para verificar que la persona elegida no haya ganado anteriormente, es decir para evitar que una persona gane mas de una vez
                if numero_ganador in record['BoletasAsignadas'] and record['Nombres'] not in personas_ganadoras:
                    #si el numero de agencia no esta en el diccionario, recordar que asignamos la "agencia" como clave, esto con el fin de que haya un ganador por cada oficina
                    if record['agencia'] not in agencias_ganadoras:
                        #toma el nombre del ganador
                        ganador = record['Nombres']
                        #agrega el numero de la agencia de la persona ganadora al diccionario como clave y como valor agrega el nro ganador
                        agencias_ganadoras[record['agencia']] = numero_ganador
                        #anado el nombre de la persona al conjunto "personas_ganadoras" para llevar control de las personas que ya han ganado 
                        personas_ganadoras.add(ganador)
                        #imprimo el diccionario solamente cuando se esta sorteando ganador por cada agencia, es decir este diccionario solo se imprime cuando se sube la base de datos para los sorteos en los que debe haber un ganador por cada oficina
                        print(agencias_ganadoras)
                        #rompe el bucle, ya se encontro un ganador para esa agencia
                        break
        #si los elementos del diccionario son 19 o es igual al numero de la variable "nroOficinas", quiere decir que ya hay un ganador por cada agencia  
        else:
            for record in data_dict.get(ultimo_archivo, []):
                #si el nro generado esta en "BoletasAsignadas" el cual columna donde estan las listas con los numeros aleatorios generados para cada persona que participará en el sorteo y si el nombre del ganador no esta en el conjunto "personas_ganadoras" 
                if numero_ganador in record['BoletasAsignadas'] and record['Nombres'] not in personas_ganadoras:
                    #al haber encontrado un ganador por oficina ya elige ganador sin importar el nro de agencia
                    ganador = record['Nombres']
                    #agrega el nro ganador al conjunto de boletas ganadoras
                    boletasGanadoras.add(numero_ganador)
                    #anado el nombre de la persona al conjunto "personas_ganadoras" para llevar control de las personas que ya han ganado 
                    personas_ganadoras.add(ganador)
                    #Se rompe el bucle for, ya que se ha encontrado un ganador.
                    break

    #imprimo las boletas que se han descartado
    print(boletas_no_aptas)


    #guardo en formato json como clave "numeroGanador" y "personaGanadora" las cuales son las que se pasan en el codigo js en la vista html y como valores "numero_ganador" y "ganador" los cuales son los que se obtienen por medio de la progrmaacion con python
    return jsonify({'numeroGanador': numero_ganador, 'personaGanadora': ganador})

#if __name__ == '__main__':
    #app.run(debug=True)
    
