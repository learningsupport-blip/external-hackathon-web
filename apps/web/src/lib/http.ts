export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function readError(body: string): string {
  try {
    const data = JSON.parse(body) as { error?: { message?: string }; detail?: { msg?: string }[] };
    return data.error?.message || data.detail?.[0]?.msg || body;
  } catch {
    return body || "Request failed";
  }
}
