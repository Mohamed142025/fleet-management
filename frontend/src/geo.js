// The phone's position when the driver presses a button. GPS works without internet; without
// permission or a fix, the step still goes through and the server marks it.
export function position(timeout = 12000) {
	return new Promise((resolve) => {
		if (!("geolocation" in navigator)) return resolve(null)
		navigator.geolocation.getCurrentPosition(
			(p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }),
			() => resolve(null),
			{ enableHighAccuracy: true, timeout, maximumAge: 3000 }
		)
	})
}

export function navigateUrl(lat, lng) {
	return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`
}
