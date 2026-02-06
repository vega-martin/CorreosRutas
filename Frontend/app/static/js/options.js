function showLoading() {
    $("#loadingOverlay").css("display", "flex");
}
function hideLoading() {
    $("#loadingOverlay").css("display", "none");
}

function desactivarTab(index, tooltipText) {
    const tabs = $("#tabs");
    tabs.tabs("disable", index);

    const li = tabs.find("ul li").eq(index);
    li.addClass("tab-disabled");

    if (tooltipText) {
        li.attr("data-tooltip", tooltipText);
    }
}

function activarTab(index) {
    const tabs = $("#tabs");
    tabs.tabs("enable", index);

    const li = tabs.find("ul li").eq(index);
    li.removeClass("tab-disabled");
    li.removeAttr("data-tooltip");
}

$(function () {
    $("#tabs").tabs();

    desactivarTab(
        1,
        "Debe generar los clusters antes de visualizar este mapa"
    );
});

document.addEventListener("DOMContentLoaded", () => {
    hideLoading();
    // --------- VARIABLES GLOBALES --------- //
    // Formulario completo
    const codiredBtn = document.getElementById('codiredBtn');
    const codiredOptions = document.getElementById('codiredOptions');
    const codiredInput = document.getElementById('codiredInput');

    const nuevoGeojson = document.getElementById('label-nuevo-geojson');
    const nuevoGeojsonBtn = document.getElementById('btn-nuevo-geojson');
    const nuevoGeojsonMsj = document.getElementById('msj-nuevo-geojson');
    const usarGeojson = document.getElementById('usar-geojson');

    const pdaBtn = document.getElementById('pdaBtn');
    const pdaOptions = document.getElementById('pdaOptions');
    const pdaInput = document.getElementById('pdaInput');

    const pdaBtnFilter = document.getElementById('pdaBtnFilter');
    const pdaOptionsFilter = document.getElementById('pdaOptionsFilter');
    const pdaInputFilter = document.getElementById('pdaInputFilter');


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
    const inputPDA = document.getElementById('pdaInputFilter');
    const signoPDA = document.getElementById('signoPDA');

    // Botones agrupamiento
    const btnAgruparGeneral = document.getElementById('btn-agrupar-general');

    const agrupamientoBtn = document.getElementById('agrupamientoBtn');
    const agrupamientoOptions = document.getElementById('agrupamientoOptions');
    const agrupamientoInput = document.getElementById('agrupamientoInput');

    const btnDescargarTabla = document.getElementById('descargarTabla');
    let dowloadType = "original"; // Determina que tabla descargar: original o cluster
    

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
            
            //let distanceFormateada = fila.distance;
            
            // if (typeof fila.distance === 'number') {
            //     distanceFormateada = fila.distance.toFixed(3); 
            // }

            if (fila.is_stop) {
                tr.style.backgroundColor = "#F2FCFF";  // light blue
            }

            //const fechaHora = `${fila.fecha}, ${fila.hora}`;
            const calleCompleta = fila.street ? `${fila.street}, ${fila.number || ''}`.trim() : '';
            //const tipoCalle = parseInt(fila.number) % 2 === 0 ? 'Par' : 'Impar';

            const celdas = [
                String(fila.cod_pda).split(",").join(", "),
                //fechaHora,
                calleCompleta,
                Number(fila.longitud_portal).toFixed(9),
                Number(fila.latitud_portal).toFixed(9),
                `${Number(fila.distance_portal).toFixed(3)} m`,
                `${Number(fila.time_accumulated).toFixed(1)} sec`,
                `${Number(fila.time_mean).toFixed(1)} sec`,
                // fila.velocidad,
                fila.type,
                fila.even_odd_count,
                fila.zigzag_count
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

    nuevoGeojsonBtn.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        const cod = codiredInput.value;
        if (!file) return;

        const formData = new FormData();
        formData.append('geojson_file', file);
        formData.append('cod', cod); // add extra data if needed

        try {
            const response = await fetch('/upload_geojson', {
                method: 'POST',
                body: formData // send FormData directly
            });

            if (!response.ok) throw new Error('Error al subir el archivo');

            const data = await response.json();
            console.log('Archivo subido con éxito:', data);
            usarGeojson.style.display = "none";
            nuevoGeojsonMsj.style.display = "block";
        } catch (err) {
            console.error(err);
            alert('Error al subir el GeoJSON');
        }
    });

    btnDescargarTabla.addEventListener("click", async () => {
        try {
            console.log(dowloadType);
            const response = await fetch("/get_table", { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: dowloadType,
                    ini: fechaInicio.value,
                    fin: fechaFin.value
                })
            });

            if (!response.ok) {
                throw new Error("Error al descargar el CSV");
            }
            // Convertir la respuesta a Blob
            const blob = await response.blob();
            // Crear URL temporal
            const url = window.URL.createObjectURL(blob);
            // Crear enlace temporal para forzar la descarga
            const a = document.createElement("a");
            a.href = url;
            a.download = "tabla.csv";
            document.body.appendChild(a);
            a.click();
            // Limpiar
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error(error);
            alert("No se pudo descargar el PDF");
        }
    });

    const cargarCodiredsInicial = () => {
        pdaOptions.innerHTML = '';
        pdaBtn.textContent = 'Selecciona una PDA';
        pdaBtn.disabled = true;
        
        nuevoGeojsonBtn.disabled = true;
        
        codiredBtn.textContent = 'Cargando códigos...';
        
        fetch('/get_unit_code')
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

        nuevoGeojsonBtn.disabled = false;
        
        nuevoGeojson.className = "blue-label";

        // Comprobar si existe un GeoJSON para el codired
        fetch('/exists_geojson', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod })
        })
        .then(response => {
            if (!response.ok) throw new Error("Error al obtener los datos del servidor");
            return response.json();
        })
        .then(data => {
            if (data.exists) {
                usarGeojson.style.display = 'block';
            } else {
                usarGeojson.style.display = 'none';
            }
        })
        .catch(err => {
            console.error(err);
        });

        pdaOptions.innerHTML = '';
        pdaBtn.disabled = true;
        
        fechaInicio.disabled = true;
        fechaFin.disabled = true;
        fechaInicio.value = "";
        fechaFin.value = "";

        cargarPdas(cod);
    };

    const cargarPdas = (cod) => {
        fetch(`/get_pdas_per_unit_code?cod=${encodeURIComponent(cod)}`)
        .then(response => response.json())
        .then(data => {
            const pdas = data.pdas;
            pdaOptions.innerHTML = "";

            if (pdas.length === 0) {
                pdaOptions.innerHTML = "<div>No hay PDAs disponibles</div>";
            } else {
                // Crear el primer div para coger todas las PDAS
                const todasDiv = document.createElement("div");
                todasDiv.dataset.value = "TODAS";
                todasDiv.textContent = "TODAS";

                attachPdaClickHandler(todasDiv, "TODAS");

                pdaOptions.appendChild(todasDiv);

                // Crear los divs de las opciones
                pdas.forEach(pda => {
                    const div = document.createElement("div");
                    div.dataset.value = pda;
                    div.textContent = pda;

                    attachPdaClickHandler(div, pda);

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

    const cargarPdasFiltrar = (cod) => {
        fetch(`/get_pdas_per_unit_code?cod=${encodeURIComponent(cod)}`)
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

                    attachPdaClickHandler(div, pda);

                    pdaOptions.appendChild(div);
                });
            }
            // Activar el dropdown
            pdaBtnFilter.textContent = "Selecciona una PDA";
            pdaBtnFilter.disabled = false;
        })
        .catch(err => {
            pdaBtnFilter.disabled = false;
            pdaInput.value = "";
            pdaBtnFilter.textContent = "PDAs no encontradas";
        });
    };

    // EventListener para las opciones de pdas
    function attachPdaClickHandler(div, pdaValue) {
        div.addEventListener('click', () => {
            pdaBtn.textContent = pdaValue;
            pdaInput.value = pdaValue;
            pdaOptions.classList.remove('show');
            cod = codiredInput.value;

            // Show message to user
            waitMessage.textContent = 'Procesando fechas válidas.';
            waitMessage.style.display = 'block';

            // Reset fields
            fechaInicio.disabled = true;
            fechaFin.disabled = true;
            fechaInicio.value = "";
            fechaFin.value = "";
            aviso.style.display = "none";
            fechasDisponibles.clear();

            // Fetch dates
            fetch(`/get_dates_per_pda_and_unit_code?pda=${encodeURIComponent(pdaValue)}&unit_code=${encodeURIComponent(cod)}`)
            .then(response => response.json())
            .then(data => {
                if (data.fechas && data.fechas.length > 0) {
                    fechaInicio.disabled = false;
                    fechaFin.disabled = false;

                    fechasDisponibles = new Set(data.fechas);

                    fechaInicio.setAttribute("min", data.fechas[0]);
                    fechaInicio.setAttribute("max", data.fechas[data.fechas.length - 1]);
                    fechaFin.setAttribute("min", data.fechas[0]);
                    fechaFin.setAttribute("max", data.fechas[data.fechas.length - 1]);
                }
            })
            .catch(() => {
                waitMessage.textContent = 'Error al cargar las fechas.';
            })
            .finally(() => {
                waitMessage.style.display = 'none';
            });
        });
    }

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
        // EVENTO GENERAR TABLA -------------------- //
        form.addEventListener("submit", (e) => {
            e.preventDefault(); // Evita el envío por defecto
            showLoading();
            validarFormulario();
        });
        // -------------------- //
        // Validar formulario
        async function validarFormulario() {
            const cod = codiredInput.value;
            const pda = pdaInput.value;
            const ini = fechaInicio.value;
            const fin = fechaFin.value;

            // Resetear los relacionado con el agurpamiento
            document.getElementById("agrupamientoInput").value = "Selecciona metodo de agrupamiento";
            document.getElementById("agrupamientoBtn").textContent = "Selecciona metodo de agrupamiento";
            document.getElementById("filtros-clus-diametro").style.display = "none";

            // Comprobar si existe un GeoJSON para el codired
            const res = await fetch('/exists_geojson', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod })
            });

            const data = await res.json();

            if (!data.exists) {
                hideLoading();
                alert("No hay un GeoJSON cargado. Debes cargar uno.");
                return false;
            }
        
            if (!cod) {
                hideLoading();
                alert("Debes introducir un código de unidad.");
                return false;
            }
        
            if (!pda) {
                hideLoading();
                alert("Debes seleccionar una PDA.");
                return false;
            } else if (pda === "TODAS") {
                document.getElementById("filtros-todas-pdas").style.display = "block";
            } else {
                document.getElementById("filtros-todas-pdas").style.display = "none";
            }
        
            if (!ini) {
                hideLoading();
                alert("Debes seleccionar una fecha de inicio.");
                return false;
            }

            if (ini > fin) {
                hideLoading();
                alert("La fecha de fin debe ser mayor que la de inicio.");
                return false;
            }

            if (!fin) {
                fin = ini;
            }

            const t_inicio = performance.now();
            
            fetch('/generar_mapa/datos_tabla', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod, pda, ini, fin })
            })
            .then(response => {
                console.log("Respuesta datos_tabla:", response.status, response.statusText);
                
                if (!response.ok) {
                    return response.json().then(errData => {
                        console.error("Error del servidor:", errData);
                        throw new Error(errData.error || `Error HTTP ${response.status}`);
                    }).catch(e => {
                        throw new Error(`Error HTTP ${response.status}: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                const t_fin = performance.now();
                console.log("Datos recibidos exitosamente:", data);

                // === Actualizar el select de PDAs en filtros ===
                const pdas = [...new Set(data.tabla.map(row => row.cod_pda))];
                pdaOptionsFilter.innerHTML = '';
                pdas.forEach(pda => {
                    const div = document.createElement('div');
                    div.classList.add('option-item');
                    div.dataset.value = pda;
                    div.textContent = pda;

                    div.addEventListener('click', () => {
                        handlePdaFilterSelection(pda);
                    });

                    pdaOptionsFilter.appendChild(div);
                });

                // Habilitar botón de filtro PDA
                pdaBtnFilter.disabled = false;
                
                // === Actualizar los resultados del resumen ===
                const resumen = data.resumen;
                document.getElementById('res-puntos').textContent = resumen.puntos_totales;
                document.getElementById('res-distancia').textContent = resumen.distancia_total;
                document.getElementById('res-tiempo').textContent = resumen.tiempo_total;
                document.getElementById('res-velocidad').textContent = resumen.velocidad_media;
                const segundos = (t_fin - t_inicio) / 1000;
                document.getElementById('res-t-ejecucion').textContent = `${segundos.toFixed(3)} s`;

                // === Actualizar los títulos ===
                document.getElementById('titulo-pda').textContent = pda;
                if (ini === fin) {
                    document.getElementById('titulo-fecha').textContent = ini;
                } else {
                    document.getElementById('titulo-fecha').textContent = ini + (fin ? " → " + fin : "");
                }
        
                // Actualizar la tabla con los datos enriquecidos (con calle, número, etc.)
                tablaDatos = data.tabla;
                // Reiniciar paginación para mostrar desde el principio
                paginaActual = 1;
                filtradoActivo = false; // Resetear filtros para ver todo
                renderPagina(paginaActual);

                // === Mostrar la tabla y los controles de paginación ===
                document.getElementById('tabla-resultados').style.display = 'block';
                document.getElementById('paginador').style.display = 'flex';
            })
            .catch(err => {
                console.error("Error capturado:", err);
                alert("Ocurrió un error al procesar la solicitud:\n\n" + err.message);
            })
            .finally(() => {
                agruparPuntosYPortales();
                desactivarTab(1, "Debe generar los clusters antes de visualizar este mapa");
                dowloadType = "original"
                btnDescargarTabla.textContent = "Descargar tabla";
                hideLoading();
            });
            
            fetch('/generar_mapa/get_mapa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cod, pda, ini, fin })
            })
            .then(response => {
                if (!response.ok) throw new Error("Error al cargar el mapa");
                return response.json();
            })
            .then(map_data => {
                console.log("Mapa cargado:", map_data.url);
                document.getElementById('iMap').src = map_data.url;
            })
            .catch(err => {
                console.error("Error al cargar mapa:", err);
            });
        }

        if (pdaInput.value === "TODAS") {
            const pdaOptionsFilterContainer = document.getElementById('pdaOptionsFilter');
            pdaOptionsFilterContainer.innerHTML = "";

            fetch(`/get_pdas_per_unit_code?cod=${encodeURIComponent(codiredInput.value)}`)
                .then(response => response.json())
                .then(data => {
                    const pdas = data.pdas;

                    if (pdas.length === 0) {
                        pdaOptionsFilterContainer.innerHTML = "<div>No hay PDAs disponibles</div>";
                    } else {
                        pdas.forEach(pda => {
                            const div = document.createElement("div");
                            div.dataset.value = pda;
                            div.textContent = pda;

                            div.addEventListener('click', () => {
                                pdaInputFilter.value = pda;
                                pdaOptionsFilterContainer.classList.remove('show');
                            });

                            pdaOptionsFilterContainer.appendChild(div);
                        });
                    }
                })
                .catch(err => {
                    console.error("Error al cargar PDAs para los filtros:", err);
                });
        }
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
            const valuePDA = document.getElementById('pdaInputFilter').value;
            const valueDiametro = document.getElementById('filtroDiametroClus').value;
            const valuePtsClus = document.getElementById('filtroNumPtsClus').value;
            
            
            if (!valueDistancia && !valueTiempo && !valueVelocidad && !valuePDA && !valueDiametro && !valuePtsClus) {
                alert("Debes seleccionar algún filtro.");
                return false;
            }

            console.log(`Valores: Distancia='${valueDistancia}', Tiempo='${valueTiempo}', Velocidad='${valueVelocidad}'`);
            
            const inputSignoDistancia = document.getElementById('distancia-signo').value;
            const inputSignoTiempo = document.getElementById('tiempo-signo').value;
            const inputSignoVelocidad = document.getElementById('velocidad-signo').value;
            const inputSignoPDA = document.getElementById('pda-signo').value;
            const cod = codiredInput.value;

            // Filtros del agrupamiento
            console.log("valor filtro diametro:")
            console.log(valueDiametro)
            console.log("valor filtro puntos:")
            console.log(valuePtsClus)

            fetch('/filter_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    distancia : valueDistancia,
                    signoDistancia : inputSignoDistancia,
                    tiempo : valueTiempo,
                    signoTiempo : inputSignoTiempo,
                    velocidad : valueVelocidad,
                    signoVelocidad: inputSignoVelocidad,
                    pda: valuePDA,
                    signoPDA: inputSignoPDA,
                    diametro: valueDiametro,
                    numPts: valuePtsClus,
                    cod: cod
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

                if(data.url != '') {
                    console.log("Mapa cargado:", data.url);
                    document.getElementById("iMapCluster").src = data.url;
                }
            })
            .catch(err => {
                console.error(err);
                alert("Ocurrió un error al procesar la solicitud.");
            });
        });


    }

    if (pdaBtnFilter) {
        pdaBtnFilter.addEventListener('click', (e) => {
            e.preventDefault();
            pdaOptionsFilter.classList.toggle('show');
        });
    }

    // Manejar selección de PDA en filtros
    const handlePdaFilterSelection = (pda) => {
        pdaBtnFilter.textContent = pda;
        pdaInputFilter.value = pda;
        pdaOptionsFilter.classList.remove('show');
    };

    // Cerrar dropdown al clickear fuera
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#pdaBtnFilter') && !e.target.closest('#pdaOptionsFilter')) {
            pdaOptionsFilter.classList.remove('show');
        }
    });

    if (btnLimpiar) {

        function limpiarFiltros() {
            inputDistancia.value = '';
            inputTiempo.value = '';
            inputVelocidad.value = '';
            inputPDA.value = '';
            pdaBtnFilter.textContent = 'Selecciona una PDA';
            document.getElementById('filtroDiametroClus').vale = '';
            document.getElementById('filtroNumPtsClus').vale = '';


            // Establecer signos por defecto
            document.getElementById('distancia-signo').value = 'menor'; 
            document.getElementById('tiempo-signo').value = 'menor';
            document.getElementById('velocidad-signo').value = 'menor';
            document.getElementById('pda-signo').value = 'igual';

            // Reiniciar el estado de filtrado
            filtradoActivo = false;
            
            // Volver a la primera página y renderizar la lista ORIGINAL
            paginaActual = 1;

            renderPagina(paginaActual); 
        }

        btnLimpiar.addEventListener('click', limpiarFiltros);
    }

    function agruparPuntosYPortales() {
        console.log("Agrupando puntos duplicados...");
        fetch('/agrupar_puntos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        })
        .then(response => {
            if (!response.ok) throw new Error("Error al agrupar puntos");
            return response.json();
        })
        .then(data => {
            console.log("Puntos agrupados exitosamente", data);
            
            // Actualizar la tabla global
            tablaDatos = data.tabla;
            
            paginaActual = 1;
            filtradoActivo = false;
            renderPagina(paginaActual);

        })
        .catch(err => {
            console.error("Error:", err);
            alert("Error al agrupar puntos: " + err.message);
        })
        .finally(() => {
            console.log("Agrupando portales...");
            fetch('/agrupar_portales', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            .then(response2 => {
                if (!response2.ok) throw new Error("Error al agrupar portales");
                return response2.json();
            })
            .then(data2 => {
                console.log("Portales agrupados exitosamente", data2);
                
                // Actualizar la tabla global
                tablaDatos = data2.tabla;
                
                paginaActual = 1;
                filtradoActivo = false;
                renderPagina(paginaActual);
            })
            .catch(err2 => {
                console.error("Error:", err2);
                alert("Error al agrupar portales: " + err2.message);
            });
        });

        agrupamientoBtn.disabled = false;
    }

    if (agrupamientoBtn) { 
        agrupamientoBtn.addEventListener('click', () => {
            agrupamientoOptions.classList.toggle('show');
        });

        const optionElements = agrupamientoOptions.querySelectorAll("div");

        optionElements.forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                agrupamientoInput.value = value;
                agrupamientoBtn.textContent = option.textContent;
                agrupamientoOptions.classList.remove('show');
                btnAgruparGeneral.disabled = false;
            });
        });
    }

    if (btnAgruparGeneral) {
        btnAgruparGeneral.addEventListener('click', (e) => {
            e.preventDefault();

            if(!agrupamientoInput) {
                alert("Seleccione un método de agrupamiento.");
                return;
            }

            const agrupamiento = agrupamientoInput.value;
            const cod = codiredInput.value;

            console.log("Agrupando portales...");

            fetch('/agrupar_por_tipo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agrupamiento, cod })
            })
            .then(response => {
                if (!response.ok) throw new Error("Error al agrupar portales");
                return response.json();
            })
            .then(data => {
                console.log("Portales agrupados exitosamente", data);
                
                // Actualizar la tabla global
                tablaDatos = data.tabla;
                
                paginaActual = 1;
                filtradoActivo = false;
                renderPagina(paginaActual);
                console.log("Mapa cargado:", data.url);
                document.getElementById("iMapCluster").src = data.url;
            })
            .catch(err => {
                console.error("Error:", err);
                alert("Error al agrupar portales: " + err.message);
            });

            if (agrupamiento === "diametro") {
                document.getElementById("filtros-clus-diametro").style.display = "block";
            } else {
                document.getElementById("filtros-clus-diametro").style.display = "none";
            }

            activarTab(1);
            dowloadType = "cluster"
            btnDescargarTabla.textContent = "Descargar clusters";
            btnAgruparGeneral.disabled = true;
        });
    }
});

