const photoInput = document.getElementById("photo");
    const photoPreview = document.getElementById("photo-preview");
    const photoPlaceholder = document.getElementById("photo-placeholder");
    const photoStatus = document.getElementById("photo-status");
    const submitButton = document.querySelector('button[type="submit"]');
    let previewUrl = null;
    let processing = false;

    function loadImage(file) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const image = new Image();
            image.onload = () => {
                URL.revokeObjectURL(url);
                resolve(image);
            };
            image.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error("This image could not be opened."));
            };
            image.src = url;
        });
    }

    function canvasBlob(canvas, quality) {
        return new Promise((resolve, reject) => {
            canvas.toBlob(blob => {
                if (blob) resolve(blob);
                else reject(new Error("Image compression failed."));
            }, "image/jpeg", quality);
        });
    }

    photoInput.addEventListener("change", async function () {
        const original = this.files && this.files[0];
        if (!original) return;

        if (original.size > 2 * 1024 * 1024) {
            alert("The original photo must be 2 MB or smaller.");
            this.value = "";
            return;
        }

        processing = true;
        submitButton.disabled = true;
        photoStatus.textContent = "Compressing photo…";

        try {
            if (!original.type.startsWith("image/")) {
                throw new Error("Please select a valid image file.");
            }

            const image = await loadImage(original);
            const maxWidth = 320;
            const maxHeight = 400;
            const scale = Math.min(
                maxWidth / image.naturalWidth,
                maxHeight / image.naturalHeight,
                1
            );

            const canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
            canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));

            const context = canvas.getContext("2d");
            context.drawImage(image, 0, 0, canvas.width, canvas.height);

            let blob;
            for (let quality = 0.82; quality >= 0.40; quality -= 0.08) {
                blob = await canvasBlob(canvas, quality);
                if (blob.size <= 100 * 1024) break;
            }

            const compressed = new File(
                [blob],
                "farmer-photo.jpg",
                { type: "image/jpeg", lastModified: Date.now() }
            );

            const transfer = new DataTransfer();
            transfer.items.add(compressed);
            photoInput.files = transfer.files;

            if (previewUrl) URL.revokeObjectURL(previewUrl);
            previewUrl = URL.createObjectURL(compressed);
            photoPreview.src = previewUrl;
            photoPreview.style.display = "block";
            photoPlaceholder.style.display = "none";

            const kb = (compressed.size / 1024).toFixed(1);
            photoStatus.textContent = `Compressed photo: ${kb} KB`;
            if (compressed.size > 100 * 1024) {
                photoStatus.textContent += " (larger than 100 KB)";
            }
        } catch (error) {
            this.value = "";
            photoStatus.textContent = "No photo selected.";
            alert(error.message || "Could not process this photo.");
        } finally {
            processing = false;
            submitButton.disabled = false;
        }
    });

    photoInput.form.addEventListener("submit", function (event) {
        if (processing) {
            event.preventDefault();
            alert("Please wait for photo compression to finish.");
        }
    });
