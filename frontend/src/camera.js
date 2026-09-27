// A photo from the back camera, made smaller (longest side 1280 px, JPEG) before it is sent.
export function takePhoto() {
	return new Promise((resolve) => {
		const input = document.createElement("input")
		input.type = "file"
		input.accept = "image/*"
		input.capture = "environment"
		input.onchange = () => {
			const file = input.files?.[0]
			if (!file) return resolve(null)
			const reader = new FileReader()
			reader.onload = () => {
				const img = new Image()
				img.onload = () => {
					const scale = Math.min(1, 1280 / Math.max(img.width, img.height))
					const canvas = document.createElement("canvas")
					canvas.width = Math.round(img.width * scale)
					canvas.height = Math.round(img.height * scale)
					canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height)
					resolve(canvas.toDataURL("image/jpeg", 0.72))
				}
				img.onerror = () => resolve(reader.result)
				img.src = reader.result
			}
			reader.readAsDataURL(file)
		}
		input.click()
	})
}
