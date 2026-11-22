import { AuthFrame } from "@/components/auth-frame";

/** The auth screens' frame (components/auth-frame.tsx), drawn once for
 *  every screen under /login, so going from Sign In to Forgot Password
 *  keeps the frame and its scene and only the new screen's rows arrive. */
export default function LoginLayout({ children }: LayoutProps<"/login">) {
  return <AuthFrame>{children}</AuthFrame>;
}
