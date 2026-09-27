// Steps pressed without internet wait here (IndexedDB), with the time they were pressed, and go
// out in order when the connection is back.
import { get, set } from "idb-keyval"

const KEY = "ms-fleet-queue"

export async function pending() {
	return (await get(KEY)) || []
}

export async function enqueue(method, args) {
	const queue = await pending()
	queue.push({ id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, method, args })
	await set(KEY, queue)
	return queue.length
}

export async function drop(id) {
	await set(KEY, (await pending()).filter((item) => item.id !== id))
}

export async function markFailed(id, message) {
	const queue = await pending()
	const item = queue.find((i) => i.id === id)
	if (item) item.error = message
	await set(KEY, queue)
}

export async function cache(key, value) {
	try {
		await set(`ms-fleet-cache:${key}`, JSON.parse(JSON.stringify(value)))
	} catch (e) {
		/* storage full or private mode: keep going online-only */
	}
}

export async function cached(key) {
	return get(`ms-fleet-cache:${key}`)
}
