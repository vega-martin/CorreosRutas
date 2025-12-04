function showLoading() {
    $("#loadingOverlay").css("display", "flex");
}
function hideLoading() {
    $("#loadingOverlay").css("display", "none");
}

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

    // const asociarPortalesBtn = document.getElementById('asociar-portales-btn');

    const btnAgruparPuntos = document.getElementById('btn-agrupar-puntos');

    const btnDescargarTabla = document.getElementById('descargarTabla');
    

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
            
            // if (typeof fila.distance === 'number') {
            //     distanceFormateada = fila.distance.toFixed(3); 
            // }

            if (fila.esParada) {
                tr.style.backgroundColor = "#F2FCFF";  // light blue
            }

            const fechaHora = `${fila.fecha}, ${fila.hora}`;
            const calleCompleta = fila.street ? `${fila.street}, ${fila.number || ''}`.trim() : '';
            //const tipoCalle = parseInt(fila.number) % 2 === 0 ? 'Par' : 'Impar';

            const celdas = [
                fila.cod_pda,
                fechaHora,
                calleCompleta,
                fila.nearest_longitud,
                fila.nearest_latitud,
                fila.distancia,
                fila.tiempo,
                fila.velocidad,
                fila.tipo
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
            const response = await fetch("/getTable", {  method: "GET",  });

            if (!response.ok) {
                throw new Error("Error al descargar el PDF");
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

        nuevoGeojsonBtn.disabled = false;
        
        nuevoGeojson.className = "blue-label";

        // Comprobar si existe un GeoJSON para el codired
        fetch('/existsGeoJSON', {
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
        fetch(`/pda_por_codired?cod=${encodeURIComponent(cod)}`)
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

    // EventListener para las opciones de pdas
    function attachPdaClickHandler(div, pdaValue) {
        div.addEventListener('click', () => {
            pdaBtn.textContent = pdaValue;
            pdaInput.value = pdaValue;
            pdaOptions.classList.remove('show');

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
            fetch(`/fechas_por_pda?pda=${encodeURIComponent(pdaValue)}`)
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

            // Comprobar si existe un GeoJSON para el codired
            const res = await fetch('/existsGeoJSON', {
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
                console.log("📊 Respuesta datos_tabla:", response.status, response.statusText);
                
                if (!response.ok) {
                    return response.json().then(errData => {
                        console.error("❌ Error del servidor:", errData);
                        throw new Error(errData.error || `Error HTTP ${response.status}`);
                    }).catch(e => {
                        throw new Error(`Error HTTP ${response.status}: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                const t_fin = performance.now();
                console.log("✅ Datos recibidos exitosamente:", data);
                
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

                // asociarPortalesBtn.disabled = false;

                if (btnAgruparPuntos) {
                    btnAgruparPuntos.style.display = 'inline-block';
                    btnAgruparPuntos.disabled = false;
                }
            })
            .catch(err => {
                console.error("❌ Error capturado:", err);
                alert("Ocurrió un error al procesar la solicitud:\n\n" + err.message);
            })
            .finally(() => {
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
                console.log("🗺️ Mapa cargado:", map_data.url);
                document.getElementById('iMap').src = map_data.url;
            })
            .catch(err => {
                console.error("❌ Error al cargar mapa:", err);
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

    if (btnAgruparPuntos) {
        btnAgruparPuntos.addEventListener('click', (e) => {
            e.preventDefault();

            console.log("🔗 Agrupando puntos duplicados...");

            fetch('/agrupar_puntos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            .then(response => {
                if (!response.ok) throw new Error("Error al agrupar puntos");
                return response.json();
            })
            .then(data => {
                console.log("✅ Puntos agrupados exitosamente", data);
                
                // Actualizar la tabla global
                tablaDatos = data.tabla;
                
                paginaActual = 1;
                filtradoActivo = false;
                renderPagina(paginaActual);

                // alert("✅ Puntos agrupados correctamente");
            })
            .catch(err => {
                console.error("❌ Error:", err);
                alert("Error al agrupar puntos: " + err.message);
            });
        });
    }

    // --------- LÓGICA BOTÓN ASOCIAR PORTALES --------- //
    // if (asociarPortalesBtn) {
    //     asociarPortalesBtn.addEventListener('click', (e) => {
    //         e.preventDefault();

    //         // Feedback visual de carga
    //         const textoOriginal = asociarPortalesBtn.textContent;
    //         asociarPortalesBtn.textContent = "Asociando...";
    //         asociarPortalesBtn.disabled = true;
    //         asociarPortalesBtn.style.cursor = "wait";
    //         const cod = codiredInput.value;

    //         fetch('/clusterizar_portales', {
    //             method: 'POST',
    //             headers: { 'Content-Type': 'application/json' },
    //             body: JSON.stringify({ cod })
    //         })
    //         .then(response => {
    //             if (!response.ok) {
    //                 // Intentar obtener mensaje de error del backend
    //                 return response.json().then(errData => {
    //                     const msg = (errData && errData.warnings && errData.warnings.length > 0) 
    //                                 ? errData.warnings[0] 
    //                                 : "Error desconocido al asociar portales.";
    //                     throw new Error(msg);
    //                 });
    //             }
    //             return response.json();
    //         })
    //         .then(data => {
    //             // Actualizar la tabla con los datos enriquecidos (con calle, número, etc.)
    //             tablaDatos = data.tabla;
                
    //             // Reiniciar paginación para mostrar desde el principio
    //             paginaActual = 1;
    //             filtradoActivo = false; // Resetear filtros para ver todo
    //             renderPagina(paginaActual);

    //             alert("Portales asociados correctamente.");
    //         })
    //         .catch(err => {
    //             console.error("Error:", err);
    //             alert("Error: " + err.message);
    //         })
    //         .finally(() => {
    //             // Restaurar estado del botón
    //             asociarPortalesBtn.textContent = textoOriginal;
    //             asociarPortalesBtn.disabled = false;
    //             asociarPortalesBtn.style.cursor = "pointer";
    //         });

    //     });
    // }
});

