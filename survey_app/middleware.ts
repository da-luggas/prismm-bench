import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// List of routes that do not require answering the questions
const PUBLIC_PATHS = ['/', '/_next', '/favicon.ico'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(path + '/'))) {
    return NextResponse.next();
  }

  // Check for required cookies
  const userAnswered = request.cookies.get('user-answered')?.value;
  const checkboxAnswered = request.cookies.get('checkbox-answered')?.value;

  if (userAnswered !== 'true' || checkboxAnswered !== 'true') {
    // Redirect to home if not answered
    const url = request.nextUrl.clone();
    url.pathname = '/';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|favicon.ico).*)'],
};
