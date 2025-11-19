document.addEventListener("DOMContentLoaded", () => {
    // --------- VARIABLES GLOBALES --------- //
    const codired = document.getElementById('codired');
    const selectBtn = document.getElementById('pdaBtn');
    const options = document.getElementById('pdaOptions');
    const pdaInput = document.getElementById('pdaInput');
    const waitMessage = document.getElementById('waitMessage');
    const fechaInicio = document.getElementById('fechaInicio');
    const fechaFin = document.getElementById('fechaFin');
    const aviso = document.getElementById('fechaAviso');
    const form = document.getElementById("forms");
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    // PAGINACIÓN Y RENDERIZADO
    let tablaDatos = [];
    let tablaFiltrada = [];
    let paginaActual = 1;
    const filasPorPagina = 50;
    let fechasDisponibles = new Set();

    // --------- FUNCIONES --------- //
    function renderPagina(pagina) {
        const tbody = document.querySelector('#tablaDatos tbody');
        tbody.innerHTML = "";

        const datos = tablaFiltrada.length ? tablaFiltrada : tablaDatos;

        const inicio = (pagina - 1) * filasPorPagina;
        const fin = inicio + filasPorPagina;
        const fragment = document.createDocumentFragment();

        const filas = datos.slice(inicio, fin);
        filas.forEach(fila => {
            const tr = document.createElement('tr');
            const celdas = [
                fila.n,
                fila.hora,
                fila.longitud,
                fila.latitud,
                fila.distancia,
                fila.tiempo,
                fila.velocidad
            ];
            celdas.forEach(valor => {
                const td = document.createElement('td');
                td.textContent = valor ?? '';
                tr.appendChild(td);
            });
            fragment.appendChild(tr);
        });

        tbody.appendChild(fragment);

        // Actualizar el texto del paginador
        document.getElementById('pagina-info').textContent =
            `Página ${pagina} de ${Math.ceil(datos.length / filasPorPagina)}`;

        // Desactivar botones si es necesario
        document.getElementById('btn-prev').style.visibility = (pagina === 1) ? 'hidden' : 'visible';
        document.getElementById('btn-next').style.visibility = pagina >= Math.ceil(datos.length / filasPorPagina) ? 'hidden' : 'visible';
    }

    // --------- EVENTOS --------- //
    if (codired) {
        selectBtn.addEventListener('click', () => {
            options.style.display = options.style.display === 'block' ? 'none' : 'block';
        });

        // Escucha el evento
        codired.addEventListener("change", () => {
            const cod = codired.value.trim();

            if (cod === "") {
                options.innerHTML = "";
                selectBtn.disabled = true;
                pdaInput.value = "";
                selectBtn.textContent = "Selecciona una PDA";
                return;
            }

            // Mensaje de cargando
            selectBtn.textContent = "Cargando...";

            // Obtener pdas disponibles desde el backend
            fetch(`/pda_por_codired?cod=${encodeURIComponent(codired.value)}`)
                .then(response => response.json())
                .then(data => {
                    const pdas = data.pdas;
                    options.innerHTML = "";

                    if (pdas.length === 0) {
                        options.innerHTML = "<div>No hay PDAs disponibles</div>";
                    } else {
                        // Crear los divs de las opciones
                        pdas.forEach(pda => {
                            const div = document.createElement("div");
                            div.dataset.value = pda;
                            div.textContent = pda;

                            // Añadir funcionalidad al div
                            div.addEventListener('click', () => {
                                selectBtn.textContent = pda;
                                pdaInput.value = pda;
                                options.style.display = 'none';

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

                            options.appendChild(div);
                        });
                    }
                    // Activar el dropdown
                    selectBtn.textContent = "Selecciona una PDA";
                    selectBtn.disabled = false;
                })
                .catch(err => {
                    selectBtn.disabled = false;
                    pdaInput.value = "";
                    selectBtn.textContent = "PDAs no encontradas";
                });

                
        });

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

        // Escuchar cambios en los campos de fecha
        fechaInicio.addEventListener("change", () => validarFecha(fechaInicio));
        fechaFin.addEventListener("change", () => validarFecha(fechaFin));
    }

    if (form) {
        // Validar formulario
        function validarFormulario() {
            const cod = codired.value;
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
    
    // --------- FILTROS --------- //
    function extraerNum(text) {
        const num = text.match(/[\d\.]+/);
        return num ? parseFloat(num[0]) : null;
    }

    function cumpleCondicion(val, comp, ref) {
        if(comp == "menor") return val < ref;
        if(comp == "menor-igual") return val <= ref;
        if(comp == "igual") return val === ref;
        if(comp == "no-igual") return val != ref;
        if(comp == "mayor") return val > ref;
        if(comp == "mayor-igual") return val >= ref;
        return false;
    }

    function filtrarTabla() {
        const filtros = [
            {
                comparador: document.getElementById("distancia-signo").value,
                valor: parseFloat(document.getElementById("filtroDistancia").value),
                campo: "distancia"
            },
            {
                comparador: document.getElementById("tiempo-signo").value,
                valor: parseFloat(document.getElementById("filtroTiempo").value),
                campo: "tiempo"
            },
            {
                comparador: document.getElementById("velocidad-signo").value,
                valor: parseFloat(document.getElementById("filtroVelocidad").value),
                campo: "velocidad"
            }
        ];

        tablaFiltrada = tablaDatos.filter(row => {
            return filtros.every(filtro => {
                if (!isNaN(filtro.valor)) {
                    const text = String(row[filtro.campo]).trim();
                    const valorFila = extraerNum(text);
                    return cumpleCondicion(valorFila, filtro.comparador, filtro.valor);
                }
                return true;
            });
        });
        
        paginaActual = 1;
        renderPagina(paginaActual)
    }

});

