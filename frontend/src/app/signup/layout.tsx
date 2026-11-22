import { AuthFrame } from "@/components/auth-frame";

/** The auth screens' frame (components/auth-frame.tsx), drawn once for
 *  every screen under /signup, as app/login/layout.tsx draws it there. */
export default function SignupLayout({ children }: LayoutProps<"/signup">) {
  return <AuthFrame>{children}</AuthFrame>;
}
