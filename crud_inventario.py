import copy
import json
import os

ARCHIVO_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventario.json")

CATALOGO_POR_DEFECTO = {
    "FAR-001": {
        "codigo": "FAR-001",
        "nombre": "Atamel Forte (Acetaminofén 650mg)",
        "categoria": "Analgésico",
        "stock_actual": 150,
        "capacidad_maxima": 300,
        "punto_reorden": 60,
        "precio_venta": 3.50,
        "costo_compra": 1.60,
        "costo_almacenamiento": 0.08,
        "costo_faltante": 1.90,
        "temp_inicial": 21.0,
        "temp_limite": 26.0
    },
    "FAR-002": {
        "codigo": "FAR-002",
        "nombre": "Lantus (Insulina Glargina 100 UI/ml)",
        "categoria": "Antidiabético refrigerado",
        "stock_actual": 90,
        "capacidad_maxima": 180,
        "punto_reorden": 45,
        "precio_venta": 28.00,
        "costo_compra": 15.50,
        "costo_almacenamiento": 0.65,
        "costo_faltante": 12.50,
        "temp_inicial": 4.0,
        "temp_limite": 8.0
    },
    "FAR-003": {
        "codigo": "FAR-003",
        "nombre": "Losartán Potásico 50mg (Genven)",
        "categoria": "Antihipertensivo",
        "stock_actual": 120,
        "capacidad_maxima": 250,
        "punto_reorden": 50,
        "precio_venta": 6.50,
        "costo_compra": 3.10,
        "costo_almacenamiento": 0.14,
        "costo_faltante": 3.40,
        "temp_inicial": 20.0,
        "temp_limite": 25.0
    }
}


def guardar_datos_json(inventario_dict):
    # Guarda el diccionario del inventario en el JSON
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump({"inventario": inventario_dict}, f, ensure_ascii=False, indent=4)


def cargar_datos_json():
    # Lee el inventario desde el JSON o inicializa los 3 productos por defecto
    if os.path.exists(ARCHIVO_JSON):
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if "inventario" in datos and isinstance(datos["inventario"], dict) and len(datos["inventario"]) > 0:
                return datos["inventario"]
        except (json.JSONDecodeError, OSError):
            pass

    inventario_inicial = copy.deepcopy(CATALOGO_POR_DEFECTO)
    guardar_datos_json(inventario_inicial)
    return inventario_inicial


def inicializar_estado_inventario(session_state):
    # Carga el inventario en st.session_state desde el JSON
    if "inventario" not in session_state:
        session_state["inventario"] = cargar_datos_json()


def obtener_catalogo(inventario_dict):
    # Devuelve la lista de productos disponibles
    return list(inventario_dict.values())


def crear_producto(
    inventario_dict,
    codigo,
    nombre,
    categoria,
    stock_actual,
    capacidad_maxima,
    punto_reorden,
    precio_venta,
    costo_compra,
    costo_almacenamiento,
    costo_faltante,
    temp_inicial=20.0,
    temp_limite=25.0
):
    # Agrega un nuevo producto al inventario y actualiza el JSON
    codigo_limpio = codigo.strip().upper()
    nombre_limpio = nombre.strip()

    if not codigo_limpio or not nombre_limpio:
        return False, "El código y el nombre del producto son obligatorios."

    if codigo_limpio in inventario_dict:
        return False, f"Ya existe un producto con el código '{codigo_limpio}'."

    if stock_actual > capacidad_maxima:
        return False, "El stock inicial no puede superar la capacidad máxima."

    inventario_dict[codigo_limpio] = {
        "codigo": codigo_limpio,
        "nombre": nombre_limpio,
        "categoria": categoria.strip() if categoria else "General",
        "stock_actual": int(stock_actual),
        "capacidad_maxima": int(capacidad_maxima),
        "punto_reorden": int(punto_reorden),
        "precio_venta": round(float(precio_venta), 2),
        "costo_compra": round(float(costo_compra), 2),
        "costo_almacenamiento": round(float(costo_almacenamiento), 2),
        "costo_faltante": round(float(costo_faltante), 2),
        "temp_inicial": round(float(temp_inicial), 1),
        "temp_limite": round(float(temp_limite), 1)
    }

    guardar_datos_json(inventario_dict)
    return True, f"Producto '{nombre_limpio}' ({codigo_limpio}) registrado correctamente."


def actualizar_producto(inventario_dict, codigo, nuevos_datos):
    # Actualiza los datos de un producto existente y guarda los cambios en el JSON
    if codigo not in inventario_dict:
        return False, f"No se encontró el producto con código '{codigo}'."

    prod = inventario_dict[codigo]
    cap_max = int(nuevos_datos.get("capacidad_maxima", prod["capacidad_maxima"]))
    nuevo_stock = int(nuevos_datos.get("stock_actual", prod["stock_actual"]))

    if nuevo_stock > cap_max:
        return False, f"El stock actual ({nuevo_stock}) en '{prod['nombre']}' supera su capacidad máxima ({cap_max})."

    prod["nombre"] = str(nuevos_datos.get("nombre", prod["nombre"])).strip()
    prod["categoria"] = str(nuevos_datos.get("categoria", prod["categoria"])).strip()
    prod["stock_actual"] = max(0, nuevo_stock)
    prod["capacidad_maxima"] = max(1, cap_max)
    prod["punto_reorden"] = max(0, int(nuevos_datos.get("punto_reorden", prod["punto_reorden"])))
    prod["precio_venta"] = round(float(nuevos_datos.get("precio_venta", prod["precio_venta"])), 2)
    prod["costo_compra"] = round(float(nuevos_datos.get("costo_compra", prod["costo_compra"])), 2)
    prod["costo_almacenamiento"] = round(float(nuevos_datos.get("costo_almacenamiento", prod["costo_almacenamiento"])), 2)
    prod["costo_faltante"] = round(float(nuevos_datos.get("costo_faltante", prod["costo_faltante"])), 2)
    prod["temp_inicial"] = round(float(nuevos_datos.get("temp_inicial", prod["temp_inicial"])), 1)
    prod["temp_limite"] = round(float(nuevos_datos.get("temp_limite", prod["temp_limite"])), 1)

    guardar_datos_json(inventario_dict)
    return True, f"Datos de '{prod['nombre']}' actualizados."


def eliminar_producto(inventario_dict, codigo):
    # Elimina un producto del catálogo asegurando que quede al menos uno
    if codigo not in inventario_dict:
        return False, "El producto seleccionado no existe."

    if len(inventario_dict) <= 1:
        return False, "Debe mantener al menos un producto en el catálogo."

    nombre_eliminado = inventario_dict[codigo]["nombre"]
    del inventario_dict[codigo]

    guardar_datos_json(inventario_dict)
    return True, f"Producto '{nombre_eliminado}' ({codigo}) eliminado."
