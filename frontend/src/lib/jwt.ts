function decodePayload(token: string): Record<string, unknown> {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

export function decodeTenantId(token: string): string {
  return (decodePayload(token)["tenant_id"] as string) ?? "";
}

export function decodeRole(token: string): string {
  return (decodePayload(token)["role"] as string) ?? "member";
}
