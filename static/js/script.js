let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        mediaRecorder.onstop = processRecording;

        mediaRecorder.start();
        isRecording = true;

        document.getElementById("status").innerText = "Recording...";
        document.getElementById("pauseBtn").disabled = false;
        document.getElementById("stopBtn").disabled = false;
    } catch (error) {
        console.error("Error accessing microphone:", error);
        alert("Microphone access denied!");
    }
}

function pauseRecording() {
    if (mediaRecorder.state === "recording") {
        mediaRecorder.pause();
        document.getElementById("status").innerText = "Recording Paused";
    } else if (mediaRecorder.state === "paused") {
        mediaRecorder.resume();
        document.getElementById("status").innerText = "Recording Resumed";
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById("status").innerText = "Processing...";
        document.getElementById("pauseBtn").disabled = true;
        document.getElementById("stopBtn").disabled = true;
    }
}

function processRecording() {
    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    audioChunks = [];

    let formData = new FormData();
    formData.append("audio", audioBlob);

    fetch('/transcribe', {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("transcribedText").value = data.text;
            document.getElementById("status").innerText = "Transcription Completed!";
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error("Error:", error));
}

function saveWord() {
    let text = document.getElementById("transcribedText").value; // Use .value for <textarea>
    if (!text) {
        alert("No text to save!");
        return;
    }

    let filename = prompt("Enter filename:", "transcription");
    if (!filename) return;

    fetch('/save', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = data.file;  // Auto download
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error("Error:", error));


}

function clear() {
    document.getElementById("transcribedText").value = "";
    document.getElementById("status").innerText = "Text Cleared"; // Optional: Adds feedback
}
