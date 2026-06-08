export { default } from "next-auth/middleware";

export const config = {
  matcher: ["/((?!$|login|register|verify-email|forgot-password|reset-password|api|_next/static|_next/image|favicon.ico).*)"],
};
