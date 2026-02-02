function showLoading() {
    $("#loadingOverlay").css("display", "flex");
}
function hideLoading() {
    $("#loadingOverlay").css("display", "none");
}

document.addEventListener("DOMContentLoaded", () => {
    hideLoading();
    // comprobar si los ficheros estan o no
    checkFiles().then(areFiles => {
        enableBtns(areFiles);
    }).finally(() => {
        checkMandatoryFiles().then(isFile => {
            console.log("Comprobando existencia de fichero a")
            console.log(!isFile)
            document.getElementById("mapaBtn").disabled = !isFile;
        });
    });

    // --- FORM A ---
    const formA = document.querySelector('form[action*="uploadFileAToBackend"]');
    const inputA = formA.querySelector('input[name="fileA"]');
    const submitA = formA.querySelector('input[type="submit"]');
    inputA.addEventListener('change', () => {
        submitA.disabled = inputA.files.length === 0;
        submitA.title = submitA.disabled ? "Se debe seleccionar un fichero" : "";
    });

    // --- FORM B+C ---
    const formBC = document.querySelector('form[action*="uploadFilesBCToBackend"]');
    const inputB = formBC.querySelector('input[name="fileB"]');
    const inputC = formBC.querySelector('input[name="fileC"]');
    const submitBC = formBC.querySelector('input[type="submit"]');
    function checkBC() {
        submitBC.disabled = !((inputB.files.length > 0) && (inputC.files.length > 0));
        submitBC.title = submitBC.disabled ? "Se deben seleccionar los dos ficheros" : "";
    }
    inputB.addEventListener('change', checkBC);
    inputC.addEventListener('change', checkBC);

    const mapaBtn = document.getElementById("mapaBtn");
    // Ajax for file A upload
    formA.addEventListener('submit', async (e) => {
        e.preventDefault();
        showLoading();
        document.getElementById('fileA-logs').value = "Subiendo fichero, aguarde unos momentos";
        const formData = new FormData(e.target);
        submitA.disabled = true;
        inputA.value = "";
        const res = await fetch(e.target.action, { method: 'POST', body: formData });
        const data = await res.json();
        document.getElementById('fileA-logs').value = data.logs;
        unifyFiles().then(areFiles => {
            enableBtns(areFiles);
        })
        .finally(() => {
            hideLoading();
            mapaBtn.disabled = false;
        });
    });

    // Ajax for files B and C upload
    formBC.addEventListener('submit', async (e) => {
        e.preventDefault();
        showLoading();
        document.getElementById('fileBC-logs').value = "Subiendo ficheros, aguarde unos momentos";
        const formData = new FormData(e.target);
        submitBC.disabled = true;
        inputB.value = "";
        inputB.files.length = 0;
        inputC.value = "";
        inputC.files.length = 0;
        const res = await fetch(e.target.action, { method: 'POST', body: formData });
        const data = await res.json();
        document.getElementById('fileBC-logs').value = data.logs;
        unifyFiles().then(areFiles => {
            enableBtns(areFiles);
        })
        .catch(err => {
            console.error("Error comprobando archivos:", err);
        })
        .finally(() => {
            hideLoading();
        });
    });

    document.getElementById("estadisticasBtn").addEventListener("click", async () => {
        try {
            const response = await fetch("/get_stadistics", {  method: "GET"  });

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
            a.download = "estadisticas.pdf";  // Nombre del archivo que verá el usuario
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

    // Para descargar los ficheros intermedios
    document.getElementById('ficherosIntermedios').addEventListener("click", async () => {
        // Descargar fichero D
        try {
            const file = "D";
            const response = await fetch("/get_generated_file", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file })
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
            a.download = "Fichero_D.csv";
            document.body.appendChild(a);
            a.click();
            // Limpiar
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error(error);
            alert("No se pudo descargar el PDF");
        }

        // Descargar fichero E
        try {
            const file = "E";
            const response = await fetch("/get_generated_file", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file })
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
            a.download = "Fichero_E.csv";
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

    const btnLogout = document.getElementById("logoutBtn");

    btnLogout.addEventListener("submit", () => {
        const mapaBtn = document.getElementById("mapaBtn");
        mapaBtn.disabled = true;
    });

});

// Confirm logout
function confirmLogout() {
    return confirm("¿Seguro que deseas cerrar la sesión y eliminar los ficheros subidos?");
}

// Comprobar si se han subido todos los archivos
function checkFiles() {
    return fetch("/check_files_status", {
        method: "GET"
    })
    .then(response => response.json())
    .then(data => data.ready)
    .catch(err => {
        console.error("Error comprobando archivos:", err);
        return false; // fallback
    });
}

// Comprobar si se han subido los archivos obligatorios (fichero A)
function checkMandatoryFiles() {
    return fetch("/check_mandatory_files_status", {
        method: "GET"
    })
    .then(response => response.json())
    .then(data => data.ready)
    .catch(err => {
        console.error("Error comprobando archivos:", err);
        return false; // fallback
    });
}

// Comprobar si se han subido todos los archivos
function unifyFiles() {
    return fetch("/try_unify_all_files", {  method: "GET"  })
    .then(response => response.json())
    .then(data => data.ready)
    .catch(err => {
        console.error("Error comprobando archivos:", err);
        return false; // fallback
    });
}

function enableBtns(areFiles) {
    const estadisticasBtn = document.getElementById("estadisticasBtn");
    const mapaBtn = document.getElementById("mapaBtn");
    const btnDescargarFicheros = document.getElementById('ficherosIntermedios');
    if (areFiles === true) {
        console.log("todos los ficheros han sido subidos");
        estadisticasBtn.disabled = false;
        mapaBtn.disabled = false;
        btnDescargarFicheros.disabled = false;
    } else {
        console.log("faltan ficheros por subir");
        estadisticasBtn.disabled = true;
        mapaBtn.disabled = true;
        btnDescargarFicheros.disabled = true;
    }
}