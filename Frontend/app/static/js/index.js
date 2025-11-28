document.addEventListener("DOMContentLoaded", () => {
    // comprobar si los ficheros estan o no
    checkFiles().then(areFiles => {
        enableBtns(areFiles);
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

    // Ajax for file A upload
    formA.addEventListener('submit', async (e) => {
        e.preventDefault();
        document.getElementById('fileA-logs').value = "Subiendo fichero, aguarde unos momentos";
        const formData = new FormData(e.target);
        submitA.disabled = true;
        inputA.value = "";
        const res = await fetch(e.target.action, { method: 'POST', body: formData });
        const data = await res.json();
        document.getElementById('fileA-logs').value = data.logs;
        unifyFiles().then(areFiles => {
            enableBtns(areFiles);
        });
    });

    // Ajax for files B and C upload
    formBC.addEventListener('submit', async (e) => {
        e.preventDefault();
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
        });
    });

    document.getElementById("estadisticasBtn").addEventListener("click", async () => {
        try {
            const response = await fetch("/getStadistics", {  method: "GET",  });

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
});
// Confirm logout
function confirmLogout() {
    return confirm("¿Seguro que deseas cerrar la sesión y eliminar los ficheros subidos?");
}

// Comprobar si se han subido todos los archivos
function checkFiles() {
    return fetch("/check_files_status", {
        method: "POST"
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
    return fetch("/try_unify_all_files", {
        method: "POST"
    })
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
    const unifyBtn = document.getElementById("unifyBtn");
    if (areFiles === true) {
        estadisticasBtn.disabled = false;
        //mapaBtn.disabled = false;
        unifyBtn.disabled = false;
    } else {
        estadisticasBtn.disabled = true;
        //mapaBtn.disabled = true;
        unifyBtn.disabled = true;
    }
}