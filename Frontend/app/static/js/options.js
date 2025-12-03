document.addEventListener("DOMContentLoaded", () => {
    // --------- VARIABLES GLOBALES --------- //
    // Formulario completo
    const codiredBtn = document.getElementById('codiredBtn');
    const codiredOptions = document.getElementById('codiredOptions');
    const codiredInput = document.getElementById('codiredInput');

    const pdaBtn = document.getElementById('pdaBtn');
    const pdaOptions = document.getElementById('pdaOptions');
    const pdaInput = document.getElementById('pdaInput');

    const waitMessage = document.getElementById('waitMessage');

    const fechaInicio = document.getElementById('fechaInicio');
    const fechaFin = document.getElementById('fechaFin');
    const aviso = document.getElementById('fechaAviso');
    
    const form = document.getElementById('forms');
    // Botones lista
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    // Filtrado
    const btnFilter = document.getElementById('btn-filtrar');
    const btnLimpiar = document.getElementById('btn-limpiar-filtros');
    const inputDistancia = document.getElementById('filtroDistancia');
    const inputTiempo = document.getElementById('filtroTiempo');
    const inputVelocidad = document.getElementById('filtroVelocidad');

    const asociarPortalesBtn = document.getElementById('asociar-portales-btn');
    

    // PAGINACIÓN Y RENDERIZADO
    let tablaDatos = [];
    let tablaFiltrada = [];
    let paginaActual = 1;
    const filasPorPagina = 50;
    let fechasDisponibles = new Set();
    let filtradoActivo = false;

    // --------- FUNCIONES --------- //
    function renderPagina(pagina) {
    const tbody = document.querySelector('#tablaDatos tbody');
    tbody.innerHTML = "";

    const datos = filtradoActivo ? tablaFiltrada : tablaDatos;

    // --- CÓDIGO DE MANEJO DE CERO RESULTADOS ---
    if (datos.length === 0 && filtradoActivo) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td colspan="11" style="text-align: center; color: #cc3333; padding: 15px;">
                ⚠️ No se encontraron registros que coincidan con los filtros aplicados.
            </td>
        `; 
        // Nota: Ajusté el colspan a 11 para que cubra todas tus columnas
        tbody.appendChild(tr);
        
        document.getElementById('paginador').style.display = 'none'; 
        document.getElementById('pagina-info').textContent = 'Página 0 de 0';
        return; 
    }

    const inicio = (pagina - 1) * filasPorPagina;
    const fin = inicio + filasPorPagina;
    const fragment = document.createDocumentFragment();

    const filas = datos.slice(inicio, fin);
    filas.forEach(fila => {
        const tr = document.createElement('tr');
        
        let distanceFormateada = fila.distance;
        
        if (typeof fila.distance === 'number') {
            distanceFormateada = fila.distance.toFixed(3); 
        }

        if (fila.esParada) {
            tr.style.backgroundColor = "#F2FCFF";  // light blue
        }

        const celdas = [
            fila.n,
            fila.hora,
            fila.longitud,
            fila.latitud,
            fila.distancia, // Esta es la otra distancia (sin redondear)
            fila.tiempo,
            fila.velocidad,
            fila.street,    
            fila.number,    
            fila.post_code, 
            distanceFormateada // Usamos la variable ya redondeada
        ];
        
        celdas.forEach(valor => {
            const td = document.createElement('td');
            
            if (valor === undefined || valor === null) {
                td.textContent = '';
            } else {
                td.textContent = valor;
            }
            tr.appendChild(td);
        });
        fragment.appendChild(tr);
    });

        tbody.appendChild(fragment);

        document.getElementById('pagina-info').textContent =
            `Página ${pagina} de ${Math.ceil(datos.length / filasPorPagina)}`;
        
        document.getElementById('btn-prev').style.visibility = (pagina === 1) ? 'hidden' : 'visible';
        document.getElementById('btn-next').style.visibility = pagina >= Math.ceil(datos.length / filasPorPagina) ? 'hidden' : 'visible';
        
        document.getElementById('paginador').style.display = 'flex';
    
    }
    // --------- EVENTOS --------- //
    document.addEventListener('click', (e) => {
        
        // Función de ayuda para ver si el clic fue dentro de un elemento
        const isClickInside = (button, options) => {
            // Si el elemento clickeado (e.target) está contenido en el botón O en las opciones, devuelve true.
            return button.contains(e.target) || options.contains(e.target);
        };

        // --- Lógica para Códigos de Unidad (codired) ---
        // Solo si los elementos existen
        if (codiredBtn && codiredOptions) {
            if (!isClickInside(codiredBtn, codiredOptions)) {
                codiredOptions.classList.remove('show');
            }
        }

        // --- Lógica para PDAs ---
        if (pdaBtn && pdaOptions) {
            if (!isClickInside(pdaBtn, pdaOptions)) {
                pdaOptions.classList.remove('show');
            }
        }
        
    });

    const cargarCodiredsInicial = () => {
        pdaOptions.innerHTML = '';
        pdaBtn.textContent = 'Selecciona una PDA';
        pdaBtn.disabled = true; 
        
        codiredBtn.textContent = 'Cargando códigos...';
        
        fetch('/codireds')
        .then(response => {
            if (!response.ok) throw new Error('Error al cargar códigos de unidad.');
            return response.json();
        })
        .then(data => {
            const cods = data.codireds;
            
            codiredOptions.innerHTML = "";

            if (cods.length === 0) {
                codiredOptions.innerHTML = "<div class='option-item'>No hay códigos de oficina disponibles</div>";
            } else {
                cods.forEach(cod => {
                    const div = document.createElement("div");
                    div.dataset.value = cod;
                    div.textContent = cod;

                    div.addEventListener('click', () => {
                        console.log("Dentro de la funcion");
                        handleCodiredSelection(cod); 
                    });

                    codiredOptions.appendChild(div);
                });
            }
            codiredBtn.textContent = "Selecciona un código de unidad";
        })
        .catch(err => {
            codiredBtn.textContent = "Error de carga inicial";
        });
    };

    const handleCodiredSelection = (cod) => {
        codiredBtn.textContent = cod;
        codiredInput.value = cod;
        
        codiredOptions.classList.remove('show');
        
        pdaOptions.innerHTML = '';
        pdaBtn.disabled = true;
        
        fechaInicio.disabled = true;
        fechaFin.disabled = true;
        fechaInicio.value = "";
        fechaFin.value = "";
        
        cargarPdas(cod); 
    };

    const cargarPdas = (cod) => {
        fetch(`/pda_por_codired?cod=${encodeURIComponent(cod)}`)
        .then(response => response.json())
        .then(data => {
            const pdas = data.pdas;
            pdaOptions.innerHTML = "";

            if (pdas.length === 0) {
                pdaOptions.innerHTML = "<div>No hay PDAs disponibles</div>";
            } else {
                // Crear los divs de las opciones
                pdas.forEach(pda => {
                    const div = document.createElement("div");
                    div.dataset.value = pda;
                    div.textContent = pda;

                    // Añadir funcionalidad al div
                    div.addEventListener('click', () => {
                        pdaBtn.textContent = pda;
                        pdaInput.value = pda;
                        pdaOptions.classList.remove('show');

                        // Mostrar mensaje de espera al usuario
                        waitMessage.textContent = 'Procesando fechas válidas.';
                        waitMessage.style.display = 'block';
                        
                        // Bloquear campos y limpiar valores
                        fechaInicio.disabled = true;
                        fechaFin.disabled = true;
                        fechaInicio.value = "";
                        fechaFin.value = "";
                        aviso.style.display = "none";
                        fechasDisponibles.clear();

                        // Obtener fechas disponibles desde el backend
                        fetch(`/fechas_por_pda?pda=${encodeURIComponent(pdaInput.value)}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.fechas && data.fechas.length > 0) {
                                    fechaInicio.disabled = false;
                                    fechaFin.disabled = true;

                                    // Guardamos fechas válidas
                                    fechasDisponibles = new Set(data.fechas);

                                    // Ajustar límites del calendario
                                    fechaInicio.setAttribute("min", data.fechas[0]);
                                    fechaInicio.setAttribute("max", data.fechas[data.fechas.length - 1]);
                                    fechaFin.setAttribute("min", data.fechas[0]);
                                    fechaFin.setAttribute("max", data.fechas[data.fechas.length - 1]);
                                }
                            })
                            .catch(error => {
                                // Mostrar mensaje de error al usuario
                                waitMessage.textContent = 'Error al cargar las fechas.'
                            })
                            .finally(() => {
                                // Ocultar mensaje de espera al usuario
                                waitMessage.style.display = 'none';
                            });
                    });

                    pdaOptions.appendChild(div);
                });
            }
            // Activar el dropdown
            pdaBtn.textContent = "Selecciona una PDA";
            pdaBtn.disabled = false;
        })
        .catch(err => {
            pdaBtn.disabled = false;
            pdaInput.value = "";
            pdaBtn.textContent = "PDAs no encontradas";
        });
    };

    // Validar fechas seleccionadas
    function validarFecha(campo) {
        const fecha = campo.value;
        if (fecha === "") return;

        if (!fechasDisponibles.has(fecha)) {
            aviso.style.display = "inline";
            campo.style.borderColor = "red";
            campo.style.backgroundColor = "#ffecec";
        } else {
            aviso.style.display = "none";
            campo.style.borderColor = "#ccc";
            campo.style.backgroundColor = "";
        }
    }

    if (codiredBtn) {
        
        codiredBtn.addEventListener('click', () => {
            codiredOptions.classList.toggle('show');
            pdaOptions.classList.remove('show');
        });

        pdaBtn.addEventListener('click', () => {
            if (!pdaBtn.disabled) {
                pdaOptions.classList.toggle('show');
                codiredOptions.classList.remove('show'); // Cierra Codired
            }
        });

        cargarCodiredsInicial();

        // Escuchar cambios en los campos de fecha
        fechaInicio.addEventListener("change", () => validarFecha(fechaInicio));
        fechaFin.addEventListener("change", () => validarFecha(fechaFin));
    }

    if (form) {
        // Validar formulario
        function validarFormulario() {
            const cod = codiredInput.value;
            const pda = pdaInput.value;
            const ini = fechaInicio.value;
            const fin = fechaFin.value;
        
            if (!cod) {
                alert("Debes introducir un código de unidad.");
                return false;
            }
        
            if (!pda) {
                alert("Debes seleccionar una PDA.");
                return false;
            }
        
            if (!ini) {
                alert("Debes seleccionar una fecha de inicio.");
                return false;
            }
        
            fetch('/generar_mapa/datos_tabla', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod, pda, ini })
            })
            .then(response => {
                if (!response.ok) throw new Error("Error al obtener los datos del servidor");
                return response.json();
            })
            .then(data => {
                // === Actualizar los resultados del resumen ===
                const resumen = data.resumen;
                document.getElementById('res-puntos').textContent = resumen.puntos_totales;
                document.getElementById('res-distancia').textContent = resumen.distancia_total;
                document.getElementById('res-tiempo').textContent = resumen.tiempo_total;
                document.getElementById('res-velocidad').textContent = resumen.velocidad_media;
        
                // === Actualizar los títulos ===
                document.getElementById('titulo-pda').textContent = pda;
                document.getElementById('titulo-fecha').textContent = ini + (fin ? " → " + fin : "");
        
                // === Guardar los datos globalmente y renderizar ===
                tablaDatos = data.tabla;
                paginaActual = 1;
                renderPagina(paginaActual);
        
                // === Mostrar la tabla y los controles de paginación ===
                document.getElementById('tabla-resultados').style.display = 'block';
                document.getElementById('paginador').style.display = 'flex';

                asociarPortalesBtn.disabled = false;
            })
            .catch(err => {
                console.error(err);
                alert("Ocurrió un error al procesar la solicitud.");
            });
        
            fetch('/generar_mapa/get_mapa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod, pda, ini })
            })
            .then(response => response.json())
            .then(map_data => {
                document.getElementById('iMap').src = map_data.url;
            });
        
        }

        // Escucha el evento
        form.addEventListener("submit", (e) => {
            e.preventDefault(); // Evita el envío por defecto
            validarFormulario();
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (!btnPrev.disabled) {
                paginaActual--;
                renderPagina(paginaActual);
            }
        });
    }

    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (!btnNext.disabled) {
                paginaActual++;
                renderPagina(paginaActual);
            }
        });
    }

    if (btnFilter) {
        btnFilter.addEventListener('click', (e) => {
            e.preventDefault();

            console.log("--> 1. EVENTO DISPARADO Y e.preventDefault() ejecutado.");

            const valueDistancia = document.getElementById('filtroDistancia').value;
            const valueTiempo = document.getElementById('filtroTiempo').value;
            const valueVelocidad = document.getElementById('filtroVelocidad').value;
            
            
            if (!valueDistancia && !valueTiempo && !valueVelocidad){
                alert("Debes seleccionar algún filtro.");
                return false;
            }

            console.log(`Valores: Distancia='${valueDistancia}', Tiempo='${valueTiempo}', Velocidad='${valueVelocidad}'`);
            
            const inputSignoDistancia = document.getElementById('distancia-signo').value;
            const inputSignoTiempo = document.getElementById('tiempo-signo').value;
            const inputSignoVelocidad = document.getElementById('velocidad-signo').value;

            fetch('/filtrar_registros', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    distancia : valueDistancia,
                    signoDistancia : inputSignoDistancia,
                    tiempo : valueTiempo,
                    signoTiempo : inputSignoTiempo,
                    velocidad : valueVelocidad,
                    signoVelocidad : inputSignoVelocidad,
                })
            })
            .then(response => {
                if (!response.ok) throw new Error("Error al obtener los datos del servidor");
                return response.json();
            })

            .then(data => {
                // === Actualizar los resultados del resumen ===
                
                // if (resumen){
                //     document.getElementById('res-puntos').textContent = resumen.puntos_totales;
                //     document.getElementById('res-distancia').textContent = resumen.distancia_total;
                //     document.getElementById('res-tiempo').textContent = resumen.tiempo_total;
                //     document.getElementById('res-velocidad').textContent = resumen.velocidad_media;
                // }
        
                // === Guardar los datos globalmente y renderizar ===
                tablaFiltrada = data.tabla;
                filtradoActivo = true;
                
                paginaActual = 1;
                renderPagina(paginaActual);
        
                // === Mostrar la tabla y los controles de paginación ===
                document.getElementById('tabla-resultados').style.display = 'block';
                document.getElementById('paginador').style.display = 'flex';
            })
            .catch(err => {
                console.error(err);
                alert("Ocurrió un error al procesar la solicitud.");
            });
        });


    }

    if (btnLimpiar) {

        function limpiarFiltros() {
            inputDistancia.value = '';
            inputTiempo.value = '';
            inputVelocidad.value = '';
            
            // Establecer signos por defecto
            document.getElementById('distancia-signo').value = 'menor'; 
            document.getElementById('tiempo-signo').value = 'menor';
            document.getElementById('velocidad-signo').value = 'menor';

            // Reiniciar el estado de filtrado
            filtradoActivo = false;
            
            // Volver a la primera página y renderizar la lista ORIGINAL
            paginaActual = 1;

            renderPagina(paginaActual); 
        }

        btnLimpiar.addEventListener('click', limpiarFiltros);
    }

    // --------- LÓGICA BOTÓN ASOCIAR PORTALES --------- //
    if (asociarPortalesBtn) {
        asociarPortalesBtn.addEventListener('click', (e) => {
            e.preventDefault();

            // Feedback visual de carga
            const textoOriginal = asociarPortalesBtn.textContent;
            asociarPortalesBtn.textContent = "Asociando...";
            asociarPortalesBtn.disabled = true;
            asociarPortalesBtn.style.cursor = "wait";

            fetch('/clusterizar_portales', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => {
                if (!response.ok) {
                    // Intentar obtener mensaje de error del backend
                    return response.json().then(errData => {
                        const msg = (errData && errData.warnings && errData.warnings.length > 0) 
                                    ? errData.warnings[0] 
                                    : "Error desconocido al asociar portales.";
                        throw new Error(msg);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Actualizar la tabla con los datos enriquecidos (con calle, número, etc.)
                tablaDatos = data.tabla;
                
                // Reiniciar paginación para mostrar desde el principio
                paginaActual = 1;
                filtradoActivo = false; // Resetear filtros para ver todo
                renderPagina(paginaActual);

                alert("Portales asociados correctamente.");
            })
            .catch(err => {
                console.error("Error:", err);
                alert("Error: " + err.message);
            })
            .finally(() => {
                // Restaurar estado del botón
                asociarPortalesBtn.textContent = textoOriginal;
                asociarPortalesBtn.disabled = false;
                asociarPortalesBtn.style.cursor = "pointer";
            });

        });
    }
});

