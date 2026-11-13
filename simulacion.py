"""
Módulo de simulación de inventario - Sector Farmacia.
Modelo estático, simulación secuencial, políticas, variable continua,
modelo híbrido y experimentación/optimización.
"""

import copy
import math
import random
import pandas as pd


# 1. MODELO ESTÁTICO DE COSTOS

def costo_estatico_producto(producto, dias=30, cantidad_comprada=None, faltantes_estimados=0):
    if cantidad_comprada is None:
        cantidad_comprada = producto["stock_actual"]

    costo_compra = cantidad_comprada * producto["costo_compra"]
    costo_almacen = producto["stock_actual"] * producto["costo_almacenamiento"] * dias
    costo_falt = faltantes_estimados * producto["costo_faltante"]

    return {
        "Código": producto["codigo"],
        "Medicamento": producto["nombre"],
        "Stock": producto["stock_actual"],
        "Unidades Compradas": int(cantidad_comprada),
        "Costo Compra ($)": round(costo_compra, 2),
        "Costo Almacén ($)": round(costo_almacen, 2),
        "Costo Faltante ($)": round(costo_falt, 2),
        "Costo Total ($)": round(costo_compra + costo_almacen + costo_falt, 2),
    }


def costo_estatico_inventario(inventario_dict, dias=30, faltantes_porcentaje=0):
    filas = []
    for prod in inventario_dict.values():
        faltantes_est = int(round(prod["stock_actual"] * faltantes_porcentaje / 100))
        filas.append(costo_estatico_producto(prod, dias=dias, faltantes_estimados=faltantes_est))

    df = pd.DataFrame(filas)
    totales = {
        "Costo Compra Total": round(df["Costo Compra ($)"].sum(), 2),
        "Costo Almacén Total": round(df["Costo Almacén ($)"].sum(), 2),
        "Costo Faltante Total": round(df["Costo Faltante ($)"].sum(), 2),
        "Costo Total General": round(df["Costo Total ($)"].sum(), 2),
    }
    return df, totales


# 2. VARIABLE CONTINUA: TEMPERATURA

def calcular_temperatura_dia(temp_inicial, dia, amplitud=1.5, periodo=15, drift=0.10, ruido=0.2):
    base = temp_inicial + drift * dia
    oscilacion = amplitud * math.sin(2 * math.pi * dia / periodo)
    perturbacion = random.uniform(-ruido, ruido)
    return round(base + oscilacion + perturbacion, 2)


# 3. MODELO HÍBRIDO: PÉRDIDA POR TEMPERATURA

def calcular_perdida_temperatura(stock, temp_actual, temp_limite, tasa_por_grado=0.05):
    exceso = temp_actual - temp_limite
    if exceso <= 0:
        return 0, 0.0
    perdida_pct = min(tasa_por_grado * exceso, 1.0)
    unidades = int(round(stock * perdida_pct))
    return unidades, perdida_pct


# 4. DEMANDA

def generar_demanda(producto, dia):
    cap = producto["capacidad_maxima"]
    media = max(1.0, cap * 0.05)
    desv = max(0.5, cap * 0.02)
    return max(1, int(round(random.gauss(media, desv))))


# 5. POLÍTICAS DE REPOSICIÓN

def politica_punto_reorden(producto, cantidad_pedido):
    if producto["stock_actual"] > producto["punto_reorden"]:
        return 0
    if cantidad_pedido is None:
        return producto["capacidad_maxima"] - producto["stock_actual"]
    return min(cantidad_pedido, producto["capacidad_maxima"] - producto["stock_actual"])


def politica_revision_periodica(producto, dia, periodo_revision, nivel_objetivo=None):
    if dia % periodo_revision != 0:
        return 0
    objetivo = nivel_objetivo if nivel_objetivo is not None else producto["capacidad_maxima"]
    objetivo = min(objetivo, producto["capacidad_maxima"])
    return max(0, objetivo - producto["stock_actual"])


# 6. SIMULACIÓN SECUENCIAL

def simular_inventario(
    inventario_dict,
    dias=30,
    politica="A",
    cantidad_pedido=None,
    periodo_revision=7,
    nivel_objetivo=None,
    amplitud_temp=1.5,
    periodo_temp=15,
    drift_temp=0.10,
    tasa_perdida_temp=0.05,
    semilla=None,
):
    if semilla is not None:
        random.seed(semilla)

    inventario_sim = copy.deepcopy(inventario_dict)

    resumen = {
        cod: {
            "ventas_totales": 0, "faltantes_totales": 0,
            "perdidas_temp_totales": 0, "pedidos_realizados": 0,
            "unidades_pedidas": 0, "ingresos": 0.0,
            "costo_compras": 0.0, "costo_almacenamiento": 0.0,
            "costo_faltante": 0.0,
        }
        for cod in inventario_sim
    }

    historial = []

    for dia in range(1, dias + 1):
        for cod, prod in inventario_sim.items():
            stock_inicial = prod["stock_actual"]
            res = resumen[cod]

            temp_dia = calcular_temperatura_dia(
                prod["temp_inicial"], dia,
                amplitud=amplitud_temp, periodo=periodo_temp, drift=drift_temp,
            )

            perdidas_u, _ = calcular_perdida_temperatura(
                stock_inicial, temp_dia, prod["temp_limite"], tasa_perdida_temp
            )
            stock_despues_temp = stock_inicial - perdidas_u
            res["perdidas_temp_totales"] += perdidas_u

            demanda = generar_demanda(prod, dia)
            ventas = min(demanda, stock_despues_temp)
            faltante = demanda - ventas
            stock_despues_ventas = stock_despues_temp - ventas

            res["ventas_totales"] += ventas
            res["faltantes_totales"] += faltante
            res["ingresos"] += ventas * prod["precio_venta"]
            res["costo_faltante"] += faltante * prod["costo_faltante"]

            prod["stock_actual"] = stock_despues_ventas
            res["costo_almacenamiento"] += stock_despues_ventas * prod["costo_almacenamiento"]

            if politica == "A":
                if isinstance(cantidad_pedido, dict):
                    q = cantidad_pedido.get(cod)
                else:
                    q = cantidad_pedido
                cantidad = politica_punto_reorden(prod, q)
            elif politica == "B":
                cantidad = politica_revision_periodica(prod, dia, periodo_revision, nivel_objetivo)
            else:
                cantidad = 0

            cantidad = max(0, cantidad)
            if cantidad > 0:
                prod["stock_actual"] += cantidad
                res["pedidos_realizados"] += 1
                res["unidades_pedidas"] += cantidad
                res["costo_compras"] += cantidad * prod["costo_compra"]

            stock_final = prod["stock_actual"]

            if stock_final == 0:
                alerta = "AGOTADO"
            elif stock_final <= prod["punto_reorden"]:
                alerta = "BAJO"
            else:
                alerta = "OK"

            historial.append({
                "Día": dia, "Código": cod, "Medicamento": prod["nombre"],
                "Stock Inicial": stock_inicial, "Temperatura (°C)": temp_dia,
                "Temp Límite (°C)": prod["temp_limite"], "Pérdidas Temp": perdidas_u,
                "Demanda": demanda, "Ventas": ventas, "Faltante": faltante,
                "Pedido": cantidad, "Stock Final": stock_final, "Alerta": alerta,
            })

    df_historial = pd.DataFrame(historial)

    totales = {
        "Ventas Totales": sum(r["ventas_totales"] for r in resumen.values()),
        "Faltantes Totales": sum(r["faltantes_totales"] for r in resumen.values()),
        "Pérdidas por Temperatura": sum(r["perdidas_temp_totales"] for r in resumen.values()),
        "Pedidos Realizados": sum(r["pedidos_realizados"] for r in resumen.values()),
        "Unidades Pedidas": sum(r["unidades_pedidas"] for r in resumen.values()),
        "Ingresos ($)": round(sum(r["ingresos"] for r in resumen.values()), 2),
        "Costo Compras ($)": round(sum(r["costo_compras"] for r in resumen.values()), 2),
        "Costo Almacenamiento ($)": round(sum(r["costo_almacenamiento"] for r in resumen.values()), 2),
        "Costo Faltante ($)": round(sum(r["costo_faltante"] for r in resumen.values()), 2),
    }
    totales["Costo Total ($)"] = round(
        totales["Costo Compras ($)"] + totales["Costo Almacenamiento ($)"] + totales["Costo Faltante ($)"], 2
    )
    base_disp = totales["Ventas Totales"] + totales["Faltantes Totales"]
    totales["Disponibilidad (%)"] = round(
        100 * totales["Ventas Totales"] / base_disp if base_disp > 0 else 100, 2
    )

    return df_historial, resumen, totales


# 7. COMPARACIÓN DE POLÍTICAS

def comparar_politicas(inventario_dict, dias=30, cantidad_pedido=None, periodo_revision=7, semilla=42):
    _, _, totA = simular_inventario(inventario_dict, dias=dias, politica="A",
                                    cantidad_pedido=cantidad_pedido, semilla=semilla)
    _, _, totB = simular_inventario(inventario_dict, dias=dias, politica="B",
                                    periodo_revision=periodo_revision, semilla=semilla)

    filas = []
    for nombre, tot in [("A - Punto de reorden", totA), ("B - Revisión periódica", totB)]:
        fila = {"Política": nombre}
        fila.update(tot)
        filas.append(fila)

    return pd.DataFrame(filas), totA, totB

# 8. EXPERIMENTACIÓN Y OPTIMIZACIÓN

def experimentar_parametros(inventario_dict, dias=30, fracciones=None, periodos=None, semilla=42):
    if fracciones is None:
        fracciones = [0.2, 0.4, 0.6, 0.8]
    if periodos is None:
        periodos = [3, 7, 10, 14]

    filas = []

    for frac in fracciones:
        cantidad_por_producto = {
            cod: int(round(frac * p["capacidad_maxima"]))
            for cod, p in inventario_dict.items()
        }
        _, _, tot = simular_inventario(inventario_dict, dias=dias, politica="A",
                                       cantidad_pedido=cantidad_por_producto, semilla=semilla)
        filas.append({
            "Política": "A - Punto de reorden",
            "Parámetro": f"Q = {int(frac * 100)}% cap.",
            "Costo Total ($)": tot["Costo Total ($)"],
            "Faltantes": tot["Faltantes Totales"],
            "Disponibilidad (%)": tot["Disponibilidad (%)"],
            "Pedidos": tot["Pedidos Realizados"],
            "Pérdidas Temp": tot["Pérdidas por Temperatura"],
        })

    for per in periodos:
        _, _, tot = simular_inventario(inventario_dict, dias=dias, politica="B",
                                       periodo_revision=per, semilla=semilla)
        filas.append({
            "Política": "B - Revisión periódica",
            "Parámetro": f"Revisión cada {per} días",
            "Costo Total ($)": tot["Costo Total ($)"],
            "Faltantes": tot["Faltantes Totales"],
            "Disponibilidad (%)": tot["Disponibilidad (%)"],
            "Pedidos": tot["Pedidos Realizados"],
            "Pérdidas Temp": tot["Pérdidas por Temperatura"],
        })

    return pd.DataFrame(filas)


def mejor_configuracion(df_experimento):
    df_orden = df_experimento.sort_values(
        by=["Costo Total ($)", "Faltantes", "Disponibilidad (%)"],
        ascending=[True, True, False],
    )
    return df_orden.iloc[0]
