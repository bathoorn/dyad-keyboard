# Working on features with git

Most of this repository is KiCad files, and **KiCad files cannot be merged.**
That single fact sets the whole workflow. Everything below follows from it.

---

## 1. The rule: one feature, one branch, off `main`

```bash
git switch main
git pull
git switch -c feature/ffc-connector
```

**Naming: `feature/<description>`**, description in lower-case kebab-case —
what the feature *is*, not which files it touches.

| Good | Poor | |
|---|---|---|
| `feature/ffc-connector` | `feature/J1` | a reference designator means nothing in six months |
| `feature/led-serpentine` | `feature/fix-leds` | "fix" says nothing about what changed |
| `feature/knob-pcb` | `feature/kicad-changes` | every branch here changes KiCad |
| `feature/split-usb-power` | `feature/new-stuff` | |

Keep it to two or three words. The branch is a label on a conversation, not a
summary of the diff.

The same discipline applies whatever prefix a branch carries — nothing below
is specific to `feature/`.

---

## 2. Why branches matter more here than in a software repo

A `.kicad_pcb` or `.kicad_sch` is a serialized object graph: UUIDs,
cross-references, and order-sensitive structure that happens to be stored as
text. Git will cheerfully three-way-merge it. The result frequently still
*parses*, which is the dangerous part — you get duplicate UUIDs, orphaned
references and silently detached nets rather than an error.

**So never let two branches touch the same board.** Not "try to avoid" —
never. If two pieces of work both need `pcb-main-right`, they are one branch
or they are sequential.

Two safe consequences of the same rule:

- **Rebase onto `main`, never merge `main` in.** Rebasing replays your
  commits one at a time, so a conflict is between one of your commits and
  `main` — a small, comprehensible thing.
- **If a KiCad file ever conflicts, do not resolve it by hand.** Take one
  side whole (`git checkout --ours` / `--theirs`) and redo the other side's
  work in KiCad. Hand-editing conflict markers in an s-expression graph is
  how you lose an afternoon of routing and not notice for a week.

> **Recommended, not yet set up:** a `.gitattributes` marking
> `*.kicad_pcb`, `*.kicad_sch`, `*.kicad_sym` and `*.kicad_mod` as
> unmergeable, so git refuses to invent a merge instead of producing a
> plausible-looking broken file.

---

## 3. Close KiCad before switching branches

KiCad holds the whole board in memory. Switch branches underneath it and the
next save writes the *old* board over the new branch's file, with no warning
and no conflict.

```bash
# close KiCad first, then:
git switch feature/whatever
```

Leftover `~*.kicad_*.lck` files mean an editor is still open or died badly.
They are gitignored, but a stale one makes KiCad claim the project is already
open — delete it once you are sure nothing is running.

`.history/` inside each project is KiCad's own version-history repo. It is
gitignored but real, and `git log` / `git show` work inside it. It is the
reason a hand-laid LED chain was recoverable once after being regenerated
away. It is a safety net, not a substitute for committing.

---

## 4. Commit as you go

Small, logical commits, each one a thing you could explain on its own. The
existing history is the reference: a descriptive sentence as the subject, then
a body that says **why**, not what the diff already shows.

Split by intent rather than by file. A typical feature here lands as
something like:

```
Add a project footprint library carrying the main FFC connector
Add the 20-pin FFC connector to the right half's schematic
Route the FFC connector on the right main PCB
Confirm the FFC part number and record the J1 pinout
```

Order them so each builds on the last — a library before the schematic that
references it, a schematic before the board updated from it.

End with the co-author trailer when Claude did the work:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 5. Hardware commits carry their numbers

A hardware change is not self-evident from its diff — 2,800 changed lines in a
`.kicad_sch` can be one connector. **Put the measurements in the message**, as
a before → after:

| Check | Command |
|---|---|
| ERC | `kicad-cli sch erc <root>.kicad_sch` |
| DRC, unconnected and parity | `kicad-cli pcb drc --schematic-parity <board>.kicad_pcb` |

Report the delta against `MANUAL_TASKS.md` §Current state, and **say plainly
which findings are expected.** A commit that moves parity from 0 to 1 is fine
if the message explains that it is a field-text mismatch clearing on the next
Update PCB from Schematic; it is alarming if the message is silent.

Never commit a board with unconnected items without saying so. That number is
the one everything else is checked against.

---

## 6. Finishing a feature

```bash
git switch main
git pull
git switch feature/ffc-connector
git rebase main          # resolve per §2 if KiCad files conflict
git switch main
git merge --ff-only feature/ffc-connector
git push
git branch -d feature/ffc-connector
```

`--ff-only` is deliberate: after a rebase it should fast-forward, and if it
refuses, something moved on `main` that you have not rebased onto. Find out
what before forcing it.

Update `MANUAL_TASKS.md` before merging, not after. It is the file the next
session reads first, and a stale baseline there is worse than no baseline —
it makes a real anomaly look like the expected state.
