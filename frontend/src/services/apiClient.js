const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

class LiteratureApi {
  async listResearchFields() {
    return this.#request("/api/research-fields");
  }

  async createResearchField(payload) {
    return this.#request("/api/research-fields", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async updateResearchField(id, payload) {
    return this.#request(`/api/research-fields/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  }

  async deleteResearchField(id) {
    return this.#request(`/api/research-fields/${id}`, { method: "DELETE" });
  }

  async listPapers(fieldId) {
    return this.#request(`/api/research-fields/${fieldId}/papers`);
  }

  async syncResearchField(fieldId) {
    return this.#request(`/api/research-fields/${fieldId}/sync`, { method: "POST" });
  }

  async updatePaperStatus(paperId, isRead) {
    return this.#request(`/api/papers/${paperId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_read: isRead })
    });
  }

  async deletePaper(paperId) {
    return this.#request(`/api/papers/${paperId}`, { method: "DELETE" });
  }

  async #request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers
      },
      ...options
    });

    if (response.status === 204) {
      return null;
    }

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(payload.detail || "Request failed", response.status);
    }
    return payload;
  }
}

export const api = new LiteratureApi();
export { ApiError };
