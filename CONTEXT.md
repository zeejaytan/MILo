# MILo Sherd Meshing

How turntable photographs of Rabati pottery sherds become 3D meshes that a conservator can trust for reassembly decisions.

## Language

**Sherd**:
A pottery fragment from the excavation, one piece of a broken vessel.
_Avoid_: part, particle

**Break face**:
The fractured surface where a sherd broke from its neighbour; the geometry reassembly reads.
_Avoid_: fracture edge (edge alone), cut surface

**Rig**:
The metal clamps, rods and jaws that hold sherds on the turntable during photography.
_Avoid_: stand, mount (unless the turntable base itself is meant)

**Pruning**:
Removing rig Gaussians after training by voting each Gaussian centre against the sherd outlines across views, then extracting from the survivors with no retraining.
_Avoid_: masking (training), culling

**Masking**:
A 2D sherd outline per photograph deciding what counts as clay at fusion time.
_Avoid_: pruning, culling, cropping

**Culling**:
Deleting vertices from a finished mesh by a rule over views or components.
_Avoid_: pruning, masking
