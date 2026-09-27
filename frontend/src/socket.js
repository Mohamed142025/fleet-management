// Frappe's realtime (socket.io): an open app hears about its trips at once.
import { io } from "socket.io-client"
import { boot } from "./boot"

export function connectSocket(onTrip) {
	const port = window.location.port ? `:${boot.socketio_port}` : ""
	const protocol = port ? "http" : "https"
	const socket = io(`${protocol}://${window.location.hostname}${port}/${boot.site_name}`, {
		withCredentials: true,
		reconnectionAttempts: 10,
	})
	socket.on("fleet_trip", onTrip)
	return socket
}
