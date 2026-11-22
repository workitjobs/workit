import { AuthFrame } from "@/components/auth-frame";

/** The auth screens' frame (components/auth-frame.tsx) round the Claude
 *  connector's consent page, a sign-in step, as app/login/layout.tsx draws
 *  it round /login. The `add` route handler beside it draws nothing. */
export default function ConnectClaudeLayout({ children }: LayoutProps<"/connect/claude">) {
  return <AuthFrame>{children}</AuthFrame>;
}
