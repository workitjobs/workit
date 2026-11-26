import { notFound, redirect } from "next/navigation";

/**
 * What an admin page does with a read that gave no data (KAN-879). Signed
 * out goes to the sign-in page. A 403 or a 404 is the 404 page, so a student
 * never learns the page exists. Any other answer (a 500, a 429, a 503) is
 * thrown to `./error.tsx`: it went to the 404 page too, so a broken query
 * told an admin the page did not exist, at the moment they needed it.
 */
export function refuse(status: number): never {
  if (status === 401) redirect("/login");
  if (status === 403 || status === 404) notFound();
  throw new Error(`The admin API answered ${status}.`);
}
