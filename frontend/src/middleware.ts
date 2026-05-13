export { default } from "next-auth/middleware";

export const config = {
  matcher: ["/((?!$|login|register|verify-email|api|_next/static|_next/image|favicon.ico).*)"],
};
