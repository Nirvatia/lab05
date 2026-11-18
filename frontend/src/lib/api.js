const BASE = '/api';

async function request(path, options = {}) {
	const res = await fetch(BASE + path, {
		headers: { 'Content-Type': 'application/json' },
		...options
	});
	if (!res.ok) {
		let detail = `${res.status} ${res.statusText}`;
		try {
			const body = await res.json();
			if (body.detail) {
				detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
			}
		} catch {
			// тело ответа не JSON — оставляем статус
		}
		throw new Error(detail);
	}
	return res.status === 204 ? null : res.json();
}

function qs(params) {
	const p = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== '' && value !== null && value !== undefined) p.set(key, value);
	}
	const s = p.toString();
	return s ? '?' + s : '';
}

export const api = {
	stats: () => request('/stats'),
	seed: (n = 1000) => request(`/seed?num_students=${n}`, { method: 'POST' }),

	students: (params) => request('/students' + qs(params)),
	createStudent: (data) => request('/students', { method: 'POST', body: JSON.stringify(data) }),
	updateStudent: (id, data) => request(`/students/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
	deleteStudent: (id) => request(`/students/${id}`, { method: 'DELETE' }),

	groups: () => request('/groups'),
	createGroup: (data) => request('/groups', { method: 'POST', body: JSON.stringify(data) }),
	updateGroup: (id, data) => request(`/groups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
	deleteGroup: (id) => request(`/groups/${id}`, { method: 'DELETE' }),

	courses: () => request('/courses'),
	createCourse: (data) => request('/courses', { method: 'POST', body: JSON.stringify(data) }),
	updateCourse: (id, data) => request(`/courses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
	deleteCourse: (id) => request(`/courses/${id}`, { method: 'DELETE' }),

	createCard: (data) => request('/cards', { method: 'POST', body: JSON.stringify(data) }),
	deleteCard: (id) => request(`/cards/${id}`, { method: 'DELETE' }),

	enroll: (data) => request('/enrollments', { method: 'POST', body: JSON.stringify(data) }),
	unenroll: (studentId, courseId) => request(`/enrollments/${studentId}/${courseId}`, { method: 'DELETE' })
};