import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const APP_DOMAIN = "app.turboman.ca";
const ROOT_DOMAIN = "turboman.ca";

const PUBLIC_PATHS = ["/login", "/register", "/verify-email", "/forgot-password", "/reset-password"];

function isPublicPath(pathname: string) {
  return pathname === "/" || PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

export default withAuth(
  function middleware(req: NextRequest) {
    const host = req.headers.get("host") ?? "";
    const { pathname } = req.nextUrl;

    // On root domain: redirect dashboard routes to app subdomain
    if (host === ROOT_DOMAIN || host === `www.${ROOT_DOMAIN}`) {
      if (!isPublicPath(pathname)) {
        const url = req.nextUrl.clone();
        url.host = APP_DOMAIN;
        return NextResponse.redirect(url);
      }
    }

    // On app subdomain: redirect landing page to root domain
    if (host === APP_DOMAIN && pathname === "/") {
      const url = req.nextUrl.clone();
      url.host = ROOT_DOMAIN;
      return NextResponse.redirect(url);
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized({ req, token }) {
        const host = req.headers.get("host") ?? "";
        const { pathname } = req.nextUrl;
        // Only require auth on app subdomain for non-public paths
        if (host === APP_DOMAIN && !isPublicPath(pathname)) {
          return !!token;
        }
        return true;
      },
    },
  }
);

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
