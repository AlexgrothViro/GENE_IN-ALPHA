async function request(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export function getJSON(url) {
  return request(url, { method: "GET", headers: { Accept: "application/json" } });
}

export function postJSON(url, body) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

export function postForm(url, formData) {
  return request(url, { method: "POST", body: formData });
}

export { request };
