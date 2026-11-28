// Each page of the window opens at its top. The page scrolls the document, so without this a switch kept the last
// page's scroll: To-dos, opened after a long scroll down Find jobs, opened at the foot of its list.
export type Scroller = { scrollTo(x: number, y: number): void };

// The page now shown, each time it renders: scrolls to the top when it is another page than the last one.
export function topOnSwitch(scroller: Scroller): (page: string) => void {
  let shown: string | undefined;
  return (page) => {
    if (shown !== undefined && page !== shown) scroller.scrollTo(0, 0);
    shown = page;
  };
}
