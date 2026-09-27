// Calls to the site. A server refusal carries err.server = true and the server's message; a
// network failure does not, which is how the offline queue tells them apart.
const API = "ms_fleet.api.driver."

export async function call(method, args = {}, { get = false } = {}) {
	const path = `/api/method/${method.includes(".") ? method : API + method}`
	const options = { credentials: "same-origin", headers: { Accept: "application/json" } }
	let url = path
	if (get) {
		url += "?" + new URLSearchParams(args)
	} else {
		options.method = "POST"
		options.headers["Content-Type"] = "application/json"
		options.headers["X-Frappe-CSRF-Token"] = window.csrf_token || ""
		options.body = JSON.stringify(args)
	}
	const response = await fetch(url, options)
	let data = {}
	try {
		data = await response.json()
	} catch (e) {
		data = {}
	}
	if (!response.ok) {
		const error = new Error(serverMessage(data) || `خطأ ${response.status}`)
		error.server = true
		error.status = response.status
		error.type = data.exc_type
		throw error
	}
	return data.message
}

function serverMessage(data) {
	if (data._server_messages) {
		try {
			return JSON.parse(data._server_messages)
				.map((m) => strip(JSON.parse(m).message))
				.join("\n")
		} catch (e) {
			/* fall through */
		}
	}
	return data.message && typeof data.message === "string" ? strip(data.message) : ""
}

function strip(html) {
	const div = document.createElement("div")
	div.innerHTML = html || ""
	return div.textContent || ""
}
