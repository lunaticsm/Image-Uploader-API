const defaultHeaders = {
  Accept: "application/json",
};

export async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { ...defaultHeaders, ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new Error(message || `Request failed (${response.status})`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function extractErrorMessage(response) {
  try {
    const data = await response.json();
    if (data?.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || item).join(", ");
    }
    return JSON.stringify(data);
  } catch {
    return response.statusText;
  }
}

export const AdminAuth = {
  storageKey: "alterbase.adminPassword",
  get() {
    return localStorage.getItem(this.storageKey) || "";
  },
  set(password) {
    localStorage.setItem(this.storageKey, password);
  },
  clear() {
    localStorage.removeItem(this.storageKey);
  },
};
