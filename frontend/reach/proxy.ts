import { NextRequest, NextResponse } from "next/server";

const protectedRoutes = ["/profile", "/home"];
const authBase = ["/auth"];
const authRoutes = ["/auth/signup", "/auth/signin"]

export function proxy(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value;
  const { pathname } = request.nextUrl;

  console.log("[proxy] path:", pathname, "| token present:", !!token);

  const isProtected = protectedRoutes.some(route => pathname.startsWith(route));
  const isBaseAuthPage = authBase.includes(pathname);
  const isAuthPage = authRoutes.includes(pathname);

  console.log("[proxy] isProtected:", isProtected, "isBaseAuthPage:", isBaseAuthPage, "isAuthPage:", isAuthPage);

  if (!token && isProtected) {
    console.log("[proxy] -> redirecting to signin (no token)");
    return NextResponse.redirect(new URL("/auth/signin", request.url));
  }

  if (isBaseAuthPage) {
    return NextResponse.redirect(new URL("/auth/signin", request.url));
  }


  if (token && isAuthPage) {
    return NextResponse.redirect(new URL("/home", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/home/:path*",
    "/profile/:path*",
    "/auth/:path*",
    "/auth",
  ],
};