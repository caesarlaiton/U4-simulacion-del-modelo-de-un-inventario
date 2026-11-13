"""
Integrantes:
    César Laiton V-27.678.619
    Eilyn Martinez V-28.434.193
    Leofran Aguilera V-31.131.068
    Pedro Marcano V-30.633.519
"""

# Instalación: pip install streamlit plotly pandas
# Ejecución: streamlit run app.py

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crud_inventario import (
    inicializar_estado_inventario,
    obtener_catalogo,
    crear_producto,
    actualizar_producto,
    eliminar_producto
)

import plotly.express as px
from simulacion import (
    costo_estatico_inventario,
    simular_inventario,
    comparar_politicas,
    experimentar_parametros,
    mejor_configuracion,
)

st.set_page_config(
    page_title="Sistema de Inventario - Farmacia",
    layout="wide"
)

inicializar_estado_inventario(st.session_state)
inventario = st.session_state["inventario"]

st.title("Sistema de inventario - Sector farmacia")
st.markdown("Administración de productos disponibles, cantidades, precios y parámetros base.")

tab_catalogo, tab_crud, tab_simulacion = st.tabs([
    "Catálogo de productos",
    "Registrar o eliminar productos",
    "Simulación de Inventario (30 Días)"
])

# 1er tab: catálogo editable y gráfico de existencias actuales
with tab_catalogo:
    st.subheader("Productos disponibles")
    st.markdown(
        "Modifique directamente los valores en la tabla y presione **Guardar cambios** "
        "para actualizar el inventario."
    )

    df_catalogo = pd.DataFrame(obtener_catalogo(inventario))

    df_editado = st.data_editor(
        df_catalogo,
        use_container_width=True,
        hide_index=True,
        disabled=["codigo"],
        column_config={
            "codigo": st.column_config.TextColumn("Código"),
            "nombre": st.column_config.TextColumn("Medicamento"),
            "categoria": st.column_config.TextColumn("Categoría"),
            "stock_actual": st.column_config.NumberColumn("Stock Actual (u.)", min_value=0, step=1),
            "capacidad_maxima": st.column_config.NumberColumn("Cap. Máxima (u.)", min_value=1, step=5),
            "punto_reorden": st.column_config.NumberColumn("Punto Reorden (u.)", min_value=0, step=5),
            "precio_venta": st.column_config.NumberColumn("Precio Venta ($)", min_value=0.1, format="$%.2f"),
            "costo_compra": st.column_config.NumberColumn("Costo Compra ($)", min_value=0.1, format="$%.2f"),
            "costo_almacenamiento": st.column_config.NumberColumn("Costo Almacén ($/día)", min_value=0.01, format="$%.2f"),
            "costo_faltante": st.column_config.NumberColumn("Costo Faltante ($)", min_value=0.1, format="$%.2f"),
            "temp_inicial": st.column_config.NumberColumn("Temp. Inicial (°C)", format="%.1f °C"),
            "temp_limite": st.column_config.NumberColumn("Temp. Límite (°C)", format="%.1f °C")
        },
        key="editor_catalogo_farmacia"
    )

    if st.button("Guardar cambios", type="primary"):
        errores = []
        for _, fila in df_editado.iterrows():
            exito, msg = actualizar_producto(inventario, fila["codigo"], fila.to_dict())
            if not exito:
                errores.append(msg)

        if errores:
            for err in errores:
                st.error(err)
        else:
            st.success("Catálogo actualizado correctamente.")
            st.rerun()

    st.divider()
    st.subheader("Existencias actuales frente a Capacidad Máxima y Punto de Reorden")

    nombres_prod = [p["nombre"] for p in inventario.values()]
    stocks_actuales = [p["stock_actual"] for p in inventario.values()]
    capacidades_max = [p["capacidad_maxima"] for p in inventario.values()]
    puntos_rop = [p["punto_reorden"] for p in inventario.values()]

    fig_barras = go.Figure()
    fig_barras.add_trace(go.Bar(
        x=nombres_prod, y=stocks_actuales,
        name="Stock Actual", marker_color="#1f77b4"
    ))
    fig_barras.add_trace(go.Bar(
        x=nombres_prod, y=puntos_rop,
        name="Punto de Reorden", marker_color="#f4a261"
    ))
    fig_barras.add_trace(go.Bar(
        x=nombres_prod, y=capacidades_max,
        name="Capacidad Máxima", marker_color="#2a9d8f"
    ))
    fig_barras.update_layout(
        barmode="group",
        xaxis_title="Medicamento",
        yaxis_title="Unidades",
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_barras, use_container_width=True)

# 2da tab: crear y eliminar productos del inventario
with tab_crud:
    col_crear, col_eliminar = st.columns([3, 2])

    with col_crear:
        st.subheader("Registrar nuevo medicamento")
        siguiente_num = len(inventario) + 1
        codigo_sugerido = f"FAR-{siguiente_num:03d}"
        while codigo_sugerido in inventario:
            siguiente_num += 1
            codigo_sugerido = f"FAR-{siguiente_num:03d}"

        with st.form("form_nuevo_producto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_cod = st.text_input("Código único:", value=codigo_sugerido)
                nuevo_nom = st.text_input("Nombre del medicamento:", placeholder="Ej. Fulgram 400mg")
                nueva_cat = st.text_input("Categoría:", value="Antibiótico")
                nuevo_stock = st.number_input("Cantidad inicial (u.):", min_value=0, max_value=2000, value=100, step=10)
                nueva_cap = st.number_input("Capacidad máxima (u.):", min_value=10, max_value=5000, value=240, step=10)
                nuevo_rop = st.number_input("Punto de reorden (u.):", min_value=0, max_value=1000, value=50, step=5)
            with c2:
                nuevo_precio = st.number_input("Precio de venta ($):", min_value=0.10, value=11.00, step=0.50)
                nuevo_costo_c = st.number_input("Costo unitario de compra ($):", min_value=0.10, value=5.40, step=0.25)
                nuevo_costo_a = st.number_input("Costo de almacenamiento ($/día):", min_value=0.01, value=0.22, step=0.02)
                nuevo_costo_f = st.number_input("Costo por faltante ($/u):", min_value=0.10, value=5.60, step=0.25)
                nueva_temp_i = st.number_input("Temperatura inicial (°C):", value=20.0, step=0.5)
                nueva_temp_l = st.number_input("Temperatura límite (°C):", value=24.0, step=0.5)

            btn_crear = st.form_submit_button("Agregar producto", use_container_width=True)
            if btn_crear:
                ok, mensaje = crear_producto(
                    inventario, nuevo_cod, nuevo_nom, nueva_cat,
                    nuevo_stock, nueva_cap, nuevo_rop,
                    nuevo_precio, nuevo_costo_c, nuevo_costo_a, nuevo_costo_f,
                    nueva_temp_i, nueva_temp_l
                )
                if ok:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)

    with col_eliminar:
        st.subheader("Eliminar medicamento")
        st.markdown("Seleccione un producto del catálogo para retirarlo del inventario:")
        opciones_borrar = {f"{cod} - {datos['nombre']}": cod for cod, datos in inventario.items()}
        seleccion_borrar = st.selectbox("Producto a eliminar:", options=list(opciones_borrar.keys()))

        if st.button("Eliminar producto", type="secondary", use_container_width=True):
            cod_a_borrar = opciones_borrar[seleccion_borrar]
            ok, mensaje = eliminar_producto(inventario, cod_a_borrar)
            if ok:
                st.success(mensaje)
                st.rerun()
            else:
                st.warning(mensaje)

# simulacion de 30 dias de inventario
with tab_simulacion:
    st.subheader("Simulación y análisis del inventario - 30 días")

    with st.expander("A) Modelo estático de costos (calculadora dinámica)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            dias_est = st.slider("Días de almacenamiento:", 1, 60, 30, key="dias_est")
        with c2:
            pct_falt = st.slider("Faltantes estimados (% del stock):", 0, 50, 0, key="pct_falt")

        df_est, tot_est = costo_estatico_inventario(inventario, dias=dias_est, faltantes_porcentaje=pct_falt)

        st.dataframe(df_est, use_container_width=True, hide_index=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Compra", f"${tot_est['Costo Compra Total']:,.2f}")
        m2.metric("Almacenamiento", f"${tot_est['Costo Almacén Total']:,.2f}")
        m3.metric("Faltantes", f"${tot_est['Costo Faltante Total']:,.2f}")
        m4.metric("TOTAL", f"${tot_est['Costo Total General']:,.2f}")

    st.divider()

    st.markdown("### Parámetros de simulación")
    c1, c2, c3 = st.columns(3)
    with c1:
        dias_sim = st.number_input("Días a simular:", 5, 90, 30, key="dias_sim")
    with c2:
        cantidad_A = st.number_input(
            "Política A - Cantidad de pedido fija (0 = llenar cap. máx.):",
            0, 500, 0, key="cant_A"
        )
    with c3:
        periodo_B = st.number_input("Política B - Revisión cada (días):", 1, 30, 7, key="per_B")

    with st.expander("Parámetros del modelo continuo (temperatura)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amp_temp = st.slider("Amplitud diaria (°C):", 0.0, 5.0, 1.5, 0.1, key="amp")
        with c2:
            drift_temp = st.slider("Calentamiento progresivo (°C/día):", 0.0, 0.5, 0.10, 0.01, key="drift")
        with c3:
            tasa_temp = st.slider("Tasa de pérdida por °C excedido:", 0.01, 0.30, 0.05, 0.01, key="tasa")

    semilla = st.number_input("Semilla aleatoria (para reproducibilidad):", 0, 9999, 42, key="sem")
    cantidad_A_final = None if cantidad_A == 0 else int(cantidad_A)

    if st.button("Ejecutar simulación completa", type="primary"):
        hist_A, res_A, tot_A = simular_inventario(
            inventario, dias=int(dias_sim), politica="A",
            cantidad_pedido=cantidad_A_final,
            amplitud_temp=amp_temp, drift_temp=drift_temp, tasa_perdida_temp=tasa_temp,
            semilla=int(semilla),
        )
        hist_B, res_B, tot_B = simular_inventario(
            inventario, dias=int(dias_sim), politica="B",
            periodo_revision=int(periodo_B),
            amplitud_temp=amp_temp, drift_temp=drift_temp, tasa_perdida_temp=tasa_temp,
            semilla=int(semilla),
        )

        st.success("Simulación completada con éxito.")

        st.markdown("### C) Comparación de políticas de reposición")
        df_comp, _, _ = comparar_politicas(
            inventario, dias=int(dias_sim),
            cantidad_pedido=cantidad_A_final, periodo_revision=int(periodo_B),
            semilla=int(semilla),
        )
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        st.markdown("### D) Evolución de la temperatura (modelo continuo)")
        df_temp = hist_A[["Día", "Medicamento", "Temperatura (°C)", "Temp Límite (°C)"]]
        
        fig_temp = px.line(
            df_temp, x="Día", y="Temperatura (°C)", color="Medicamento",
            title="Temperatura del almacén por medicamento vs. límite",
        )
        
        # Dibujamos las líneas punteadas SIN texto (para que no se monten)
        for med in df_temp["Medicamento"].unique():
            lim = df_temp[df_temp["Medicamento"] == med]["Temp Límite (°C)"].iloc[0]
            fig_temp.add_hline(y=lim, line_dash="dot", line_color="gray", opacity=0.5)
            
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Mostramos los límites ordenados debajo de la gráfica
        limites_texto = " | ".join([
            f"**{med}**: {df_temp[df_temp['Medicamento'] == med]['Temp Límite (°C)'].iloc[0]}°C" 
            for med in df_temp["Medicamento"].unique()
        ])
        st.caption(f"🌡️ **Límites de temperatura por producto:** {limites_texto}")

        st.markdown("### E) Evolución del stock por política")
        colA, colB = st.columns(2)
        with colA:
            st.caption("Política A - Punto de reorden")
            st.line_chart(hist_A, x="Día", y="Stock Final", color="Medicamento")
        with colB:
            st.caption("Política B - Revisión periódica")
            st.line_chart(hist_B, x="Día", y="Stock Final", color="Medicamento")

        st.markdown("### F) Alertas registradas")
        alertas = hist_A[hist_A["Alerta"] != "OK"][
            ["Día", "Medicamento", "Alerta", "Stock Final", "Faltante", "Pérdidas Temp"]
        ]
        if alertas.empty:
            st.info("No se registraron alertas de stock bajo o agotado.")
        else:
            st.dataframe(alertas, use_container_width=True, hide_index=True)

        st.markdown("### G) Experimentación y optimización")
        df_exp = experimentar_parametros(inventario, dias=int(dias_sim), semilla=int(semilla))
        st.dataframe(df_exp, use_container_width=True, hide_index=True)

        mejor = mejor_configuracion(df_exp)
        st.success(
            f"**Configuración recomendada:** {mejor['Política']} con {mejor['Parámetro']} — "
            f"Costo Total ${mejor['Costo Total ($)']:.2f}, "
            f"Faltantes {int(mejor['Faltantes'])}, "
            f"Disponibilidad {mejor['Disponibilidad (%)']}%."
        )

        with st.expander("Ver historial día por día (Política A)"):
            st.dataframe(hist_A, use_container_width=True, hide_index=True)
        with st.expander("Ver historial día por día (Política B)"):
            st.dataframe(hist_B, use_container_width=True, hide_index=True)
