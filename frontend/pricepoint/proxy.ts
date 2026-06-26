import { NextRequest, NextResponse } from "next/server";

const protectedRoutes = ["/home", "/profile"];
const authBase = ["/auth"];
const authRoutes = ["/auth/signup", "/auth/signin"]

export function proxy(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value;

  const { pathname } = request.nextUrl;

  const isProtected = protectedRoutes.some(route =>
    pathname.startsWith(route)
  );

  const isBaseAuthPage = authBase.includes(pathname);
  const isAuthPage = authRoutes.includes(pathname)

  if (!token && isProtected) {
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
    "/dashboard/:path*",
    "/profile/:path*",
    "/auth/:path*",
    "/auth",
  ],
};