"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useTransition,
  type ReactNode,
} from "react";

import { TrashIcon } from "@/components/icons";
import { SelectionAction, SelectionBar, SelectionMenu } from "@/components/selection-bar";
import { DropdownMenuItem } from "@/components/shadcn/dropdown-menu";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/shadcn/dialog";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

import { STAGE_COLOR, STAGE_ICON, STAGE_LABEL } from "../stage-colors";
import type { Application } from "../tracker";
import { unsaveJob } from "../jobs/actions";
import { setApplicationStage, type PickableStage } from "./actions";
import { StatusIcon } from "./icons";
import { undoStage } from "./[jobId]/undo";

/** The stages a pick can move to: the stage menu's (`StageMenu`). */
const PICKABLE: PickableStage[] = ["applied", "interviewing", "offer", "rejected"];

type Picked = Pick<Application, "id" | "role" | "stage">;

type TrackerPick = {
  /** The picked rows, by application id. */
  picked: ReadonlySet<string>;
  setPicked: (ids: Iterable<string>) => void;
  /** The rows the table shows, which a pick is kept within. */
  shown: Picked[];
  setShown: (rows: Picked[]) => void;
};

const Context = createContext<TrackerPick | null>(null);

/**
 * The Tracker's picked rows (2026-11-11, as Documents' resumes and Up
 * Next): shared by the table, whose rows hold the select boxes
 * (./list.tsx), and the filter row, which the bar lies over
 * (./filter-bar.tsx). They are siblings on the page, so the pick lives
 * here, around both.
 */
export function TrackerPickProvider({ children }: { children: ReactNode }) {
  const [picked, set] = useState<ReadonlySet<string>>(new Set());
  const [shown, setShown] = useState<Picked[]>([]);
  const setPicked = useCallback((ids: Iterable<string>) => set(new Set(ids)), []);
  const value = useMemo(() => ({ picked, setPicked, shown, setShown }), [picked, setPicked, shown]);
  return <Context value={value}>{children}</Context>;
}

export function useTrackerPick() {
  const pick = useContext(Context);
  if (!pick) throw new Error("useTrackerPick needs TrackerPickProvider");
  return pick;
}

/**
 * The bar over the Tracker's filter row while any shown row is picked
 * (components/selection-bar.tsx): the count, **Status** (a menu of Applied,
 * Interviewing, Offer and Rejected, as each row's stage menu; a saved job
 * among the picks asks first, since it cannot go back to Saved; the toast's
 * Undo moves each back to its own stage), then **Remove** as a trash glyph
 * while every pick is a saved job, as a closed posting's Remove does (an
 * application stays: the API refuses to unsave one). Escape or Select All
 * clears the pick.
 */
export function TrackerSelectionBar() {
  const { picked, setPicked, shown } = useTrackerPick();
  const router = useRouter();
  const toast = useToast();
  const [pending, start] = useTransition();
  const [asking, setAsking] = useState<PickableStage | null>(null);
  const [removing, setRemoving] = useState(false);
  const rows = shown.filter((row) => picked.has(row.id));
  if (rows.length === 0) return null;
  const clear = () => setPicked([]);
  const allSaved = rows.every((row) => row.stage === "saved");
  const jobs = rows.length === 1 ? "job" : "jobs";

  function move(next: PickableStage) {
    const moving = rows.filter((row) => row.stage !== next);
    start(async () => {
      const results = await Promise.all(moving.map((row) => setApplicationStage(row.id, next)));
      const failed = results.filter((result) => result.error).length;
      clear();
      router.refresh();
      const back = moving.flatMap((row, i) => {
        const from = undoStage(row.stage);
        return from && !results[i].error ? [{ id: row.id, from }] : [];
      });
      toast.show({
        message:
          failed === 0
            ? `Moved ${moving.length} to ${STAGE_LABEL[next]}.`
            : `Moved ${moving.length - failed}. ${failed} couldn't be moved.`,
        action:
          back.length > 0
            ? {
                label: "Undo",
                onClick: async () => {
                  await Promise.all(back.map(({ id, from }) => setApplicationStage(id, from)));
                  router.refresh();
                },
              }
            : undefined,
      });
    });
  }

  function remove() {
    setRemoving(false);
    start(async () => {
      const results = await Promise.all(rows.map((row) => unsaveJob(row.id)));
      const failed = results.filter((result) => result.error).length;
      clear();
      router.refresh();
      toast.show({
        message:
          failed === 0
            ? `Removed ${rows.length} saved ${jobs}.`
            : `Removed ${rows.length - failed}. ${failed} couldn't be removed.`,
      });
    });
  }

  return (
    <>
      <SelectionBar
        count={rows.length}
        onClear={clear}
        className="absolute top-1/2 left-0 -translate-y-1/2"
      >
        <SelectionMenu label="Status" icon={<StatusIcon />} disabled={pending}>
          {PICKABLE.map((stage) => {
            const Icon = STAGE_ICON[stage];
            return (
              <DropdownMenuItem
                key={stage}
                onClick={() => {
                  if (rows.some((row) => row.stage === "saved")) setAsking(stage);
                  else move(stage);
                }}
              >
                <Icon className={`size-4 ${STAGE_COLOR[stage].onTint}`} />
                {STAGE_LABEL[stage]}
              </DropdownMenuItem>
            );
          })}
        </SelectionMenu>
        {allSaved && (
          <SelectionAction
            danger
            iconOnly
            label="Remove"
            icon={<TrashIcon />}
            disabled={pending}
            onClick={() => setRemoving(true)}
          />
        )}
      </SelectionBar>

      {/* As the stage menu asks (./[jobId]/tracker-controls.tsx). */}
      <Dialog open={asking != null} onOpenChange={(open) => !open && setAsking(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-subtitle font-semibold">
              Move {rows.length} to {asking && STAGE_LABEL[asking]}?
            </DialogTitle>
            <DialogDescription>
              A saved job that moves can&apos;t go back to Saved. It takes today as its applied date
              if it has none.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="secondary">Cancel</Button>} />
            <Button
              onClick={() => {
                if (asking) move(asking);
                setAsking(null);
              }}
            >
              Move to {asking && STAGE_LABEL[asking]}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* As a closed posting's Remove All asks (./closed-saved.tsx). */}
      <Dialog open={removing} onOpenChange={setRemoving}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-subtitle font-semibold">
              Remove {rows.length} saved {jobs}?
            </DialogTitle>
            <DialogDescription>
              {rows.length === 1 ? "It leaves" : "They leave"} the Tracker. You can save{" "}
              {rows.length === 1 ? "it" : "them"} again from the Jobs page while the posting is
              open.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="secondary">Cancel</Button>} />
            <Button variant="destructive" onClick={remove}>
              Remove {rows.length}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
