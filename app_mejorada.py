import os
import shutil
import threading
import queue
import tkinter as tk

from tkinter import (ttk, filedialog, messagebox)

from collections import defaultdict
from datetime import datetime


# APP
class AgrupadorFicherosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agrupador de ficheros")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Cola para comunicar el hilo de trabajo con la interfaz
        self.cola = queue.Queue()

        # Control del proceso
        self.procesando = False
        self.detener_proceso = False

        # Variables de la interfaz
        self.directorio_var = tk.StringVar()

        self.caracteres_iniciales_var = tk.IntVar(value=10)
        self.min_ficheros_var = tk.IntVar(value=2)

        self.recursivo_var = tk.BooleanVar(value=False)
        self.caracteres_finales_var = tk.IntVar(value=5)

        self.progreso_var = tk.DoubleVar(value=0)
        self.estado_var = tk.StringVar(value="Seleccione un directorio para comenzar.")

        self.crear_interfaz()

        self.root.after(100, self.procesar_cola)  # Comprobar periódicamente mensajes del hilo

    # INTERFAZ
    def crear_interfaz(self):
        # Marco principal
        marco_principal = ttk.Frame(self.root, padding=15)
        marco_principal.pack(fill="both", expand=True)

        # Título
        titulo = ttk.Label(marco_principal, text="Agrupador de ficheros", font=("Arial", 20, "bold"))
        titulo.pack(pady=(0, 15))

        # Selección de directorio
        marco_directorio = ttk.LabelFrame(marco_principal, text="Directorio", padding=10)
        marco_directorio.pack(fill="x", pady=(0, 10))

        entrada_directorio = ttk.Entry(marco_directorio, textvariable=self.directorio_var)
        entrada_directorio.pack(side="left", fill="x", expand=True, padx=(0, 10))

        boton_examinar = ttk.Button(marco_directorio, text="Examinar...", command=self.seleccionar_directorio)
        boton_examinar.pack(side="right")

        # Parámetros
        marco_parametros = ttk.LabelFrame(marco_principal, text="Parámetros de agrupación", padding=10)
        marco_parametros.pack(fill="x", pady=(0, 10))

        # Caracteres iniciales
        ttk.Label(marco_parametros, text="Caracteres iniciales:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.spin_iniciales = ttk.Spinbox(marco_parametros, from_=1, to=999, textvariable=self.caracteres_iniciales_var,
                                          width=10)
        self.spin_iniciales.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Mínimo de ficheros
        ttk.Label(marco_parametros, text="Mínimo de ficheros por grupo:").grid(row=1, column=0, sticky="w", padx=5,
                                                                               pady=5)
        self.spin_min_ficheros = ttk.Spinbox(marco_parametros, from_=2, to=999999, textvariable=self.min_ficheros_var,
                                             width=10)
        self.spin_min_ficheros.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Recursividad por caracteres
        self.checkbox_recursivo = ttk.Checkbutton(
            marco_parametros,
            text=("Activar agrupación recursiva (reducir caracteres progresivamente)"),
            variable=self.recursivo_var,
            command=self.actualizar_estado_recursividad
        )

        self.checkbox_recursivo.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(15, 5))

        # Caracteres finales
        ttk.Label(marco_parametros, text="Caracteres finales:").grid(row=3, column=0, sticky="w", padx=5, pady=5)

        self.spin_finales = ttk.Spinbox(marco_parametros, from_=1, to=998, textvariable=self.caracteres_finales_var,
                                        width=10, state="disabled")
        self.spin_finales.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        self.recorrer_subdirectorios_var = tk.BooleanVar(value=False)

        self.checkbox_subdirectorios = ttk.Checkbutton(
            marco_parametros,
            text="Buscar también en subdirectorios existentes",
            variable=self.recorrer_subdirectorios_var
        )
        self.checkbox_subdirectorios.grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=(10, 5))

        # Información
        informacion = ttk.Label(marco_parametros,
                                text=("Ejemplo: 10 caracteres iniciales y 5 finales → 10, 9, 8, 7, 6 y 5 caracteres."),
                                foreground="gray"
                                )
        informacion.grid(row=5, column=0, columnspan=3, sticky="w", padx=5, pady=(10, 0))

        # Botones
        marco_botones = ttk.Frame(marco_principal)
        marco_botones.pack(fill="x", pady=(5, 10))

        self.boton_iniciar = ttk.Button(marco_botones, text="▶ Iniciar agrupación", command=self.iniciar)
        self.boton_iniciar.pack(side="left", padx=(0, 10))

        self.boton_detener = ttk.Button(marco_botones, text="■ Detener", command=self.detener, state="disabled")
        self.boton_detener.pack(side="left")

        # Barra de progreso
        marco_progreso = ttk.Frame(marco_principal)
        marco_progreso.pack(fill="x", pady=(0, 10))
        self.barra_progreso = ttk.Progressbar(marco_progreso, variable=self.progreso_var, maximum=100)
        self.barra_progreso.pack(fill="x")
        ttk.Label(marco_progreso, textvariable=self.estado_var).pack(anchor="w", pady=(5, 0))

        # Registro
        marco_registro = ttk.LabelFrame(marco_principal, text="Registro del proceso", padding=5)
        marco_registro.pack(fill="both", expand=True)
        self.texto_registro = tk.Text(marco_registro, wrap="none", font=("Consolas", 9))

        scrollbar_vertical = ttk.Scrollbar(marco_registro, orient="vertical", command=self.texto_registro.yview)
        scrollbar_horizontal = ttk.Scrollbar(marco_registro, orient="horizontal", command=self.texto_registro.xview)

        self.texto_registro.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
        self.texto_registro.grid(row=0, column=0, sticky="nsew")

        scrollbar_vertical.grid(row=0, column=1, sticky="ns")
        scrollbar_horizontal.grid(row=1, column=0, sticky="ew")

        marco_registro.rowconfigure(0, weight=1)
        marco_registro.columnconfigure(0, weight=1)

    # RECURRENCIA
    def actualizar_estado_recursividad(self):
        if self.recursivo_var.get():
            self.spin_finales.config(state="normal")
        else:
            self.spin_finales.config(state="disabled")

    def seleccionar_directorio(self):
        directorio = filedialog.askdirectory(title="Seleccione el directorio")
        if directorio:
            self.directorio_var.set(directorio)

    def escribir_log(self, mensaje):
        ahora = datetime.now().strftime("%H:%M:%S")
        texto = f"[{ahora}] {mensaje}\n"
        self.texto_registro.insert("end", texto)
        self.texto_registro.see("end")

    def iniciar(self):
        # Evitar dos procesos simultáneos
        if self.procesando:
            return

        directorio = self.directorio_var.get().strip()
        if not directorio:
            messagebox.showwarning("Directorio", "Seleccione un directorio.")
            return

        if not os.path.isdir(directorio):
            messagebox.showerror("Directorio incorrecto", "El directorio seleccionado no existe.")
            return

        # Obtener parámetros
        try:
            caracteres_iniciales = int(self.caracteres_iniciales_var.get())
            min_ficheros = int(self.min_ficheros_var.get())
            caracteres_finales = int(self.caracteres_finales_var.get())
        except (ValueError, TypeError):
            messagebox.showerror("Parámetros incorrectos", "Los parámetros deben ser números enteros.")
            return

        # Validar caracteres
        if caracteres_iniciales < 1:
            messagebox.showerror("Parámetros incorrectos", "Los caracteres iniciales deben ser mayores que 0.")
            return

        if min_ficheros < 2:
            messagebox.showerror("Parámetros incorrectos", "El mínimo de ficheros debe ser al menos 2.")
            return

        if self.recursivo_var.get():  # Validar recursividad
            if caracteres_finales < 1:
                messagebox.showerror("Parámetros incorrectos", "Los caracteres finales deben ser mayores que 0.")
                return

            if caracteres_finales >= caracteres_iniciales:
                messagebox.showerror("Parámetros incorrectos",
                                     "Los caracteres finales deben ser menores que los caracteres iniciales.")
                return
        else:
            caracteres_finales = caracteres_iniciales

        # Confirmación
        niveles = (
            list(range(caracteres_iniciales, caracteres_finales - 1, -1))
            if self.recursivo_var.get()
            else [caracteres_iniciales]
        )

        mensaje = (
            f"Directorio:\n{directorio}\n\n"
            f"Caracteres: {', '.join(map(str, niveles))}\n"
            f"Mínimo de ficheros: {min_ficheros}\n"
            f"Recorrer subdirectorios: "
            f"{'Sí' if self.recorrer_subdirectorios_var.get() else 'No'}\n\n"
            f"¿Desea iniciar el proceso?"
        )

        confirmar = messagebox.askyesno("Confirmar agrupación", mensaje)
        if not confirmar:
            return

        # Preparar interfaz
        self.procesando = True
        self.detener_proceso = False

        self.boton_iniciar.config(state="disabled")
        self.boton_detener.config(state="normal")
        self.progreso_var.set(0)
        self.texto_registro.delete("1.0", "end")

        self.escribir_log("============================================")
        self.escribir_log("INICIO DEL PROCESO")
        self.escribir_log(f"Directorio: {directorio}")
        self.escribir_log(f"Caracteres: {niveles}")
        self.escribir_log(f"Mínimo de ficheros: {min_ficheros}")
        self.escribir_log("============================================")

        # Ejecutar en segundo plano
        hilo = threading.Thread(
            target=self.ejecutar_agrupacion,
            args=(
                directorio,
                niveles,
                min_ficheros,
                self.recorrer_subdirectorios_var.get()
            ),
            daemon=True
        )
        hilo.start()

    # DETENER
    def detener(self):
        if not self.procesando:
            return

        confirmar = messagebox.askyesno("Detener proceso", "¿Desea detener el proceso?")
        if confirmar:
            self.detener_proceso = True
            self.escribir_log("Solicitando detención...")

    def obtener_archivos(self, directorio, recorrer_subdirectorios):
        archivos = []

        if recorrer_subdirectorios:
            for raiz, directorios, nombres in os.walk(directorio):
                # Evitar problemas con enlaces simbólicos
                directorios[:] = [
                    d for d in directorios
                    if not os.path.islink(os.path.join(raiz, d))
                ]

                for nombre in nombres:
                    ruta = os.path.join(raiz, nombre)
                    if os.path.isfile(ruta):
                        archivos.append(ruta)
        else:
            try:
                for nombre in os.listdir(directorio):
                    ruta = os.path.join(directorio, nombre)
                    if os.path.isfile(ruta):
                        archivos.append(ruta)
            except Exception as e:
                self.cola.put(("error", f"No se pudo leer el directorio: {e}"))
        return archivos

    # AGRUPACIÓN
    def ejecutar_agrupacion(self, directorio, niveles_caracteres, min_ficheros, recorrer_subdirectorios):
        total_movidos = 0
        total_grupos = 0
        total_errores = 0

        try:
            # Obtener todos los archivos
            archivos_disponibles = self.obtener_archivos(directorio, recorrer_subdirectorios)

            if not archivos_disponibles:
                self.cola.put(
                    (
                        "log",
                        "No se encontraron ficheros."
                    )
                )

                self.cola.put(
                    (
                        "finalizado",
                        {
                            "movidos": 0,
                            "grupos": 0,
                            "errores": 0
                        }
                    )
                )

                return

            self.cola.put(
                (
                    "log",
                    f"Ficheros encontrados: "
                    f"{len(archivos_disponibles)}"
                )
            )

            # Procesar cada nivel
            cantidad_niveles = len(niveles_caracteres)
            for indice_nivel, caracteres in enumerate(niveles_caracteres):
                if self.detener_proceso:
                    self.cola.put(("log", "Proceso detenido por el usuario."))
                    break
                self.cola.put(("nivel", caracteres))

                # Crear grupos
                grupos = defaultdict(list)
                for ruta in archivos_disponibles:
                    if self.detener_proceso:
                        break
                    nombre = os.path.basename(ruta)

                    # ----------------------------------------
                    # Si el nombre tiene menos caracteres
                    # se utiliza el nombre completo.
                    # ----------------------------------------
                    prefijo = nombre[:caracteres]
                    # No permitir prefijos vacíos
                    if not prefijo:
                        continue
                    grupos[prefijo].append(ruta)

                # Buscar grupos válidos
                grupos_validos = {
                    prefijo: archivos
                    for prefijo, archivos in grupos.items()
                    if len(archivos) >= min_ficheros
                }

                self.cola.put(
                    (
                        "log",
                        (
                            f"Nivel {caracteres} caracteres: "
                            f"{len(grupos_validos)} grupos "
                            f"válidos encontrados."
                        )
                    )
                )

                # Procesar grupos
                for prefijo, archivos in grupos_validos.items():
                    if self.detener_proceso:
                        break
                    try:
                        # Determinar dónde crear la carpeta
                        #
                        # Si los archivos están en diferentes
                        # subdirectorios, cada grupo se crea
                        # dentro del directorio donde se
                        # encuentra cada archivo.
                        #
                        # Si todos están en el mismo directorio,
                        # se crea una única carpeta.
                        #
                        archivos_por_directorio = defaultdict(list)

                        for ruta in archivos:
                            carpeta_origen = os.path.dirname(ruta)
                            archivos_por_directorio[carpeta_origen].append(ruta)

                        # Mover por cada directorio
                        for carpeta_origen, archivos_grupo in (archivos_por_directorio.items()):
                            if self.detener_proceso:
                                break

                            # Solo crear grupo si sigue
                            # cumpliendo el mínimo
                            if len(archivos_grupo) < min_ficheros:
                                continue

                            carpeta_destino = os.path.join(carpeta_origen, prefijo)

                            # Evitar conflictos
                            if os.path.exists(carpeta_destino):
                                if not os.path.isdir(carpeta_destino):
                                    mensaje = (
                                        f'ERROR: No se puede crear '
                                        f'"{prefijo}" porque ya existe '
                                        f'un fichero con ese nombre.'
                                    )

                                    self.cola.put(("error", mensaje))
                                    total_errores += 1
                                    continue
                            else:
                                os.makedirs(carpeta_destino)
                                self.cola.put(
                                    (
                                        "log",
                                        (
                                            f'Creado grupo: '
                                            f'"{prefijo}" '
                                            f'({len(archivos_grupo)} '
                                            f'ficheros)'
                                        )
                                    )
                                )

                            movidos_grupo = 0

                            # Mover archivos
                            for ruta_origen in archivos_grupo:
                                if self.detener_proceso:
                                    break

                                if not os.path.exists(ruta_origen):
                                    continue

                                nombre = os.path.basename(ruta_origen)
                                ruta_destino = os.path.join(carpeta_destino, nombre)

                                # No mover si ya está en destino
                                if os.path.abspath(ruta_origen) == os.path.abspath(ruta_destino):
                                    continue

                                # Si ya existe, no sobrescribir
                                if os.path.exists(ruta_destino):
                                    mensaje = (f'ERROR: Ya existe: {ruta_destino}')
                                    self.cola.put(("error", mensaje))
                                    total_errores += 1
                                    continue

                                # Mover
                                try:
                                    shutil.move(ruta_origen, ruta_destino)

                                    movidos_grupo += 1
                                    total_movidos += 1
                                    self.cola.put(("movido", (f'{nombre} -> {prefijo}/')))
                                except Exception as e:
                                    total_errores += 1
                                    self.cola.put(("error", (f'Error moviendo "{nombre}": {e}')))

                            # Contabilizar grupo
                            if movidos_grupo >= min_ficheros:
                                total_grupos += 1
                                self.cola.put(
                                    (
                                        "grupo",
                                        (
                                            f'Grupo "{prefijo}" '
                                            f'completado: '
                                            f'{movidos_grupo} ficheros.'
                                        )
                                    )
                                )

                            elif movidos_grupo > 0:

                                self.cola.put(
                                    (
                                        "log",
                                        (
                                            f'Grupo "{prefijo}" '
                                            f'parcial: '
                                            f'{movidos_grupo} ficheros.'
                                        )
                                    )
                                )

                    except Exception as e:
                        total_errores += 1
                        self.cola.put(("error", f'Error procesando grupo "{prefijo}": {e}'))

                # Actualizar lista de archivos disponibles
                if not self.detener_proceso:
                    archivos_disponibles = [
                        ruta
                        for ruta in archivos_disponibles
                        if os.path.exists(ruta)
                    ]

                # Progreso por nivel

                progreso = ((indice_nivel + 1) / cantidad_niveles * 100)
                self.cola.put(("progreso", progreso))

                # Si no quedan archivos, terminar
                if not archivos_disponibles:
                    self.cola.put(("log", "Todos los ficheros han sido agrupados."))
                    break

            # Finalización
            self.cola.put(
                (
                    "finalizado",
                    {
                        "movidos": total_movidos,
                        "grupos": total_grupos,
                        "errores": total_errores
                    }
                )
            )

        except Exception as e:
            self.cola.put(("error", f"Error general: {e}"))
            self.cola.put(
                (
                    "finalizado",
                    {
                        "movidos": total_movidos,
                        "grupos": total_grupos,
                        "errores": total_errores + 1
                    }
                )
            )

    # PROCESAR COLA
    def procesar_cola(self):
        try:
            while True:
                tipo, datos = self.cola.get_nowait()

                # Log
                if tipo == "log":
                    self.escribir_log(datos)
                elif tipo == "nivel":  # Nivel
                    self.estado_var.set(f"Procesando grupos de {datos} caracteres...")
                    self.escribir_log("--------------------------------------------")
                    self.escribir_log(f"Buscando grupos de {datos} caracteres...")
                elif tipo == "movido":  # Archivo movido
                    self.escribir_log(f"  ✓ {datos}")
                elif tipo == "grupo":  # Grupo
                    self.escribir_log(f"  ★ {datos}")
                elif tipo == "error":  # Error
                    self.escribir_log(f"  ✗ {datos}")
                elif tipo == "progreso":  # Progreso
                    self.progreso_var.set(datos)
                elif tipo == "finalizado":  # Finalizado
                    self.procesando = False
                    self.boton_iniciar.config(state="normal")
                    self.boton_detener.config(state="disabled")
                    self.progreso_var.set(100)
                    self.estado_var.set("Proceso terminado.")
                    self.escribir_log("============================================")
                    self.escribir_log("PROCESO FINALIZADO")
                    self.escribir_log(f"Ficheros movidos: {datos['movidos']}")
                    self.escribir_log(f"Grupos creados: {datos['grupos']}")
                    self.escribir_log(f"Errores: {datos['errores']}")
                    self.escribir_log("============================================")

                    if not self.detener_proceso:
                        messagebox.showinfo("Proceso terminado",
                                            (
                                                f"Proceso terminado.\n\n"
                                                f"Ficheros movidos: "
                                                f"{datos['movidos']}\n"
                                                f"Grupos creados: "
                                                f"{datos['grupos']}\n"
                                                f"Errores: "
                                                f"{datos['errores']}"
                                            )
                                            )
        except queue.Empty:
            pass

        # Volver a comprobar la cola
        self.root.after(100, self.procesar_cola)


# MAIN
if __name__ == "__main__":
    root = tk.Tk()
    app = AgrupadorFicherosApp(root)
    root.mainloop()
