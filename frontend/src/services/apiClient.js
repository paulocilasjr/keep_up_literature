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

  async listPapers(fieldId, filters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.starred) params.set("starred", "true");
    if (filters.search?.trim()) params.set("search", filters.search.trim());
    const query = params.toString();
    return this.#request(`/api/research-fields/${fieldId}/papers${query ? `?${query}` : ""}`);
  }

  async syncResearchField(fieldId, lookbackDays = null) {
    const query = lookbackDays ? `?lookback_days=${lookbackDays}` : "";
    return this.#request(`/api/research-fields/${fieldId}/sync${query}`, { method: "POST" });
  }

  async updatePaper(paperId, changes) {
    return this.#request(`/api/papers/${paperId}`, {
      method: "PATCH",
      body: JSON.stringify(changes)
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
