# Trabajo Práctico – Transferencia de Archivos sobre UDP/TCP

Este proyecto implementa protocolos de transferencia de archivos (Stop & Wait y Selective Repeat) utilizando **UDP** en un entorno de red simulado con **Mininet**.

---

## 🚀 Requisitos

- Linux (probado en Ubuntu dentro de Vagrant)
- Mininet instalado
- Python 3
- Open vSwitch

---

## ⚙️ Levantar Mininet

Primero, crear una topología con 3 hosts y 1 switch:

```bash
sudo mn --topo single,3 --mac --switch ovsk --controller none
```

Esto levanta los hosts:
- `h1` → servidor  
- `h2`, `h3` → clientes

Probar conectividad:

```bash
pingall
```

---

## 📂 Servidor

En el host `h1`:

```bash
xterm h1
python3 start-server.py -H 10.0.0.1 -p 9000 -s ./storage
```

- `-H` → IP del servidor dentro de Mininet (`10.0.0.1`)  
- `-p` → puerto  
- `-s` → carpeta donde se guardan los archivos recibidos  

---

## 📤 Subida de archivos (upload)

En el cliente (ejemplo `h2`):

```bash
xterm h2
python3 upload.py -H 10.0.0.1 -p 9000 -s /home/Desktop/Facultad/tp1/src/ -n archivo_5MB.bin -r sw
```

El path en el parametro -s es un ejemplo. Se debe completar con el path del directorio donde se encuentra el archivo.

Parámetros:
- `-v` → Modo verboso (opcional)
- `-H` → IP del servidor  
- `-p` → puerto  
- `-s` → Path del archivo a enviar
- `-n` → Nombre del archivo
- `-r` → protocolo (`sw` = Stop & Wait, `sr` = Selective Repeat)  

---

## 📥 Descarga de archivos (download)

En el cliente (ejemplo `h3`):

```bash
xterm h3
python3 download.py -H 10.0.0.1 -p 9000 -d /home/Desktop/Facultad/tp1/src/guarda/archivoDescargado -n archivo_5MB.bin -r sw
```

El path en el parametro -d es un ejemplo. Se debe completar con el path del archivo donde se quiera guardar. Si el archivo no existe, el programa lo crea.
En el parametro -n el cliente debe saber el nombre del archivo almacenado en el server para poder descargarlo.

Parámetros:
- `-v` → Modo verboso (opcional)
- `-H` → IP del servidor  
- `-p` → puerto  
- `-d` → Path de almacenado de archivo
- `-n` → Nombre del archivo a descargar
- `-r` → protocolo (`sw` = Stop & Wait, `sr` = Selective Repeat)  
---

## 🌐 Simulación de red con pérdida/delay

Configurar pérdida de paquetes en un host:

```bash
h2 tc qdisc replace dev h2-eth0 root netem loss 10%
```

Volver a condiciones normales:

```bash
h2 tc qdisc del dev h2-eth0 root
```

---

## 📝 Notas

- Stop & Wait es más simple pero menos eficiente bajo pérdida/delay.  
- Selective Repeat aprovecha ventanas de transmisión para mejorar throughput.  
- Los experimentos deben probar con distintos valores de pérdida y delay (0%, 5%, 10%).  
