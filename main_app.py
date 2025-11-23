def gestion_electricidad():
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
    # --- RESET TEMPORAL CON CONFIRMACIÓN ---
    st.error("🚨 RESET TEMPORAL DE DATOS")
    
    # Inicializar estado de confirmación de reset
    if 'show_reset_confirmation' not in st.session_state:
        st.session_state.show_reset_confirmation = False
    
    if not st.session_state.show_reset_confirmation:
        if st.button("🔄 Resetear datos a vacío (SOLO PRIMERA VEZ)", type="secondary"):
            st.session_state.show_reset_confirmation = True
            st.rerun()
    else:
        st.warning("⚠️ ¿ESTÁS SEGURO DE QUE QUIERES RESETEAR LOS DATOS?")
        st.error("🚨 ESTA ACCIÓN ELIMINARÁ TODOS LOS PLANES EXISTENTES Y NO SE PUEDE DESHACER")
        
        col_reset_confirm, col_reset_cancel = st.columns(2)
        with col_reset_confirm:
            if st.button("✅ SÍ, RESETEAR TODO", type="primary"):
                df_vacio = pd.DataFrame(columns=[
                    'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                    'punta', 'valle', 'total_potencia', 'activo'
                ])
                df_vacio.to_csv("data/precios_luz.csv", index=False)
                st.success("✅ Datos reseteados correctamente. Ahora puedes crear tus propios planes.")
                st.session_state.show_reset_confirmation = False
                # Limpiar también otros estados si existen
                if hasattr(st.session_state, 'editing_plan'):
                    st.session_state.editing_plan = None
                if hasattr(st.session_state, 'show_confirmation'):
                    st.session_state.show_confirmation = False
                st.rerun()
        
        with col_reset_cancel:
            if st.button("❌ Cancelar reset", type="secondary"):
                st.session_state.show_reset_confirmation = False
                st.info("Reset cancelado")
                st.rerun()
    # --- FIN RESET TEMPORAL CON CONFIRMACIÓN ---
    
    # Explicación del campo "activo"
    with st.expander("💡 ¿Qué significa 'Plan activo'?"):
        st.info("""
        **Plan Activo = ✅** → El plan aparece en las calculadoras para los usuarios
        **Plan Inactivo = ❌** → El plan NO aparece en las calculadoras (pero se mantiene en el sistema)
        
        *Útil para desactivar planes temporales o promociones finalizadas sin eliminarlos.*
        """)
    
    # Cargar datos actuales
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        # Si el DataFrame está vacío, crear uno nuevo
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo'
        ])
    
    # Mostrar datos actuales con opción de edición
    st.write("### 📊 Planes Actuales")
    if not df_luz.empty:
        # Crear columnas para mostrar planes
        cols = st.columns(3)
        planes_activos = df_luz[df_luz['activo'] == True]
        planes_inactivos = df_luz[df_luz['activo'] == False]
        
        with cols[0]:
            st.write("**✅ Planes Activos**")
            for _, plan in planes_activos.iterrows():
                if st.button(
                    f"📝 {plan['plan']}", 
                    key=f"edit_{plan['plan']}",
                    use_container_width=True
                ):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with cols[1]:
            st.write("**❌ Planes Inactivos**")
            for _, plan in planes_inactivos.iterrows():
                if st.button(
                    f"📝 {plan['plan']}", 
                    key=f"edit_inactive_{plan['plan']}",
                    use_container_width=True
                ):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with cols[2]:
            st.write("**📈 Resumen**")
            st.metric("Planes Activos", len(planes_activos))
            st.metric("Planes Inactivos", len(planes_inactivos))
            st.metric("Total Planes", len(df_luz))
            
    else:
        st.info("No hay planes configurados aún")
    
    # Formulario para añadir/editar planes
    st.write("### ➕ Añadir/✏️ Editar Plan")
    
    # Inicializar estado de edición si no existe
    if 'editing_plan' not in st.session_state:
        st.session_state.editing_plan = None
    
    # Si estamos editando, mostrar info
    if st.session_state.editing_plan is not None:
        plan_actual = st.session_state.editing_plan
        st.warning(f"✏️ Editando: **{plan_actual['plan']}**")
        
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_plan = None
            st.rerun()
    
    # Inicializar estado de confirmación
    if 'show_confirmation' not in st.session_state:
        st.session_state.show_confirmation = False
    if 'pending_plan' not in st.session_state:
        st.session_state.pending_plan = None
    if 'pending_action' not in st.session_state:
        st.session_state.pending_action = None
    
    # FORMULARIO PRINCIPAL
    with st.form("form_plan_electricidad"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Si estamos editando, bloquear el nombre
            if st.session_state.editing_plan is not None:
                nombre_plan = st.text_input("Nombre del Plan*", 
                                          value=st.session_state.editing_plan['plan'],
                                          disabled=True)
                st.info("⚠️ El nombre no se puede modificar al editar")
            else:
                nombre_plan = st.text_input("Nombre del Plan*", placeholder="Ej: IMPULSA 24h")
            
            precio_original = st.number_input("Precio Original kWh*", min_value=0.0, format="%.3f", 
                                            value=st.session_state.editing_plan['precio_original_kwh'] if st.session_state.editing_plan else 0.170)
            con_pi = st.number_input("Con PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan['con_pi_kwh'] if st.session_state.editing_plan else 0.130)
        
        with col2:
            sin_pi = st.number_input("Sin PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan['sin_pi_kwh'] if st.session_state.editing_plan else 0.138)
            punta = st.number_input("Punta €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan['punta'] if st.session_state.editing_plan else 0.116)
            valle = st.number_input("Valle €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan['valle'] if st.session_state.editing_plan else 0.046)
        
        with col3:
            # Calcular automáticamente el total de potencia
            total_potencia = punta + valle
            st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                          value=total_potencia, disabled=True, key="total_potencia_display")
            st.caption("💡 Calculado automáticamente: Punta + Valle")
            
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan['activo'] if st.session_state.editing_plan else True)
        
        # BOTÓN DE SUBMIT
        if st.session_state.editing_plan is not None:
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
            action_type = "actualizar"
        else:
            submitted = st.form_submit_button("➕ Crear Nuevo Plan", type="primary")
            action_type = "crear"
        
        if submitted:
            if not nombre_plan:
                st.error("❌ El nombre del plan es obligatorio")
            else:
                # Preparar datos para confirmación
                st.session_state.pending_plan = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo
                }
                st.session_state.pending_action = action_type
                st.session_state.show_confirmation = True
                st.rerun()
    
    # MOSTRAR CONFIRMACIÓN (FUERA DEL FORM)
    if st.session_state.show_confirmation:
        st.markdown("---")
        st.warning("⚠️ CONFIRMACIÓN REQUERIDA")
        
        if st.session_state.pending_action == "actualizar":
            st.write(f"¿Estás seguro de que quieres ACTUALIZAR el plan '{st.session_state.pending_plan['plan']}'?")
        else:
            st.write(f"¿Estás seguro de que quieres CREAR el nuevo plan '{st.session_state.pending_plan['plan']}'?")
        
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ Sí, confirmar", type="primary", key="confirm_yes"):
                # Ejecutar la acción
                nuevo_plan = st.session_state.pending_plan
                
                # Añadir o actualizar el plan
                if nuevo_plan['plan'] in df_luz['plan'].values:
                    # Actualizar plan existente
                    idx = df_luz[df_luz['plan'] == nuevo_plan['plan']].index[0]
                    for key, value in nuevo_plan.items():
                        df_luz.at[idx, key] = value
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' actualizado correctamente")
                else:
                    # Añadir nuevo plan
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan])], ignore_index=True)
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' añadido correctamente")
                
                # Guardar y limpiar estado
                df_luz.to_csv("data/precios_luz.csv", index=False)
                st.session_state.editing_plan = None
                st.session_state.show_confirmation = False
                st.session_state.pending_plan = None
                st.session_state.pending_action = None
                st.rerun()
        
        with col_cancel:
            if st.button("❌ Cancelar", type="secondary", key="confirm_no"):
                st.session_state.show_confirmation = False
                st.session_state.pending_plan = None
                st.session_state.pending_action = None
                st.info("Operación cancelada")
                st.rerun()
    
    # Opción para eliminar planes (FUERA DE CUALQUIER FORM)
    if not df_luz.empty and st.session_state.editing_plan is None and not st.session_state.show_confirmation:
        st.write("### 🗑️ Eliminar Plan")
        plan_a_eliminar = st.selectbox("Selecciona plan a eliminar", df_luz['plan'].unique())
        
        if st.button("Eliminar Plan Seleccionado", type="secondary"):
            st.session_state.pending_elimination = plan_a_eliminar
            st.rerun()
    
    # Confirmación para eliminación
    if hasattr(st.session_state, 'pending_elimination'):
        st.markdown("---")
        st.error("🚨 ELIMINACIÓN PERMANENTE")
        st.write(f"¿Estás seguro de que quieres ELIMINAR permanentemente el plan '{st.session_state.pending_elimination}'?")
        
        col_conf_del, col_can_del = st.columns(2)
        with col_conf_del:
            if st.button("✅ Sí, eliminar", type="primary"):
                df_luz = df_luz[df_luz['plan'] != st.session_state.pending_elimination]
                df_luz.to_csv("data/precios_luz.csv", index=False)
                st.success(f"✅ Plan '{st.session_state.pending_elimination}' eliminado correctamente")
                if hasattr(st.session_state, 'pending_elimination'):
                    del st.session_state.pending_elimination
                st.rerun()
        
        with col_can_del:
            if st.button("❌ Cancelar eliminación"):
                if hasattr(st.session_state, 'pending_elimination'):
                    del st.session_state.pending_elimination
                st.info("Eliminación cancelada")
                st.rerun()