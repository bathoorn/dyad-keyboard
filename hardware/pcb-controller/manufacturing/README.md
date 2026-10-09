# Controller module — manufacturing files

Exported from `dyad-controller.kicad_pcb` / `.kicad_sch` at commit **89c11e8**
(35 × 57 mm, 2-layer, 1.6 mm). At export: DRC 0 errors, 0 unconnected;
schematic parity 14 field-copy differences only; ERC 145 (inherited baseline).

These are generated files. Regenerate them after any board or schematic
change rather than editing them — the commands are at the end.

## Files

| File | For |
|---|---|
| `dyad-controller-gerbers.zip` | PCB order — upload this. Shared by both halves. |
| `fab/` | The same Gerber and drill files unzipped, so changes show up in diffs. |
| `dyad-controller-left-bom.csv` / `-left-cpl.csv` | Assembly, **left** half |
| `dyad-controller-right-bom.csv` / `-right-cpl.csv` | Assembly, **right** half |

**Two assembly variants, one bare board.** Each half fits a different main
FFC and split USB-C (`docs/CONTROLLER.md` §2):

| | Main FFC | Split USB-C |
|---|---|---|
| Left half | J6 | J9 |
| Right half | J7 | J10 |

Each BOM/CPL pair leaves out the other half's two connectors. Everything
else (38 parts per half) is common. All parts are on the **bottom** side.

## Ordering notes (JLCPCB)

- **Check part rotations in the placement preview.** KiCad's bottom-side
  rotations and JLCPCB's often disagree for some packages — diodes, SOT-23,
  the USB-C receptacles and the FFC connectors are the usual suspects.
- **Extended parts** carry a one-time loading fee each; expect the RP2040,
  flash, ABM8-272-T3 crystal, FFC connectors and TS-1187A buttons among them.
- Still open before ordering (`docs/CONTROLLER.md` §6): the LDO rating
  against the Phase 1 current measurement, button reachability in the case,
  and the FFC cable type (A or B).

## Regenerating

From the repository root, with KiCad 10:

```bash
cd hardware/pcb-controller
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts --subtract-soldermask --check-zones -o manufacturing/fab/ dyad-controller.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-separate-th -o manufacturing/fab/ dyad-controller.kicad_pcb
(cd manufacturing/fab && zip -q -X ../dyad-controller-gerbers.zip *)
kicad-cli sch export bom --fields 'Value,Reference,Footprint,LCSC,${DNP}' --labels 'Comment,Designator,Footprint,LCSC Part #,DNP' --group-by 'Value,Footprint,LCSC' --ref-range-delimiter '' --exclude-dnp -o bom-all.csv dyad-controller.kicad_sch
kicad-cli pcb export pos --format csv --units mm --side both -o pos-all.csv dyad-controller.kicad_pcb
```

Then split `bom-all.csv` / `pos-all.csv` per half: drop J7 and J10 for the
left, J6 and J9 for the right; BOM columns Comment, Designator, Footprint,
LCSC Part #; CPL columns Designator, Mid X, Mid Y, Layer, Rotation.
